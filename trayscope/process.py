"""Gamescope process management using asyncio."""

import asyncio
import os
import signal
from typing import Callable, Optional

from trayscope.config import Config


class GamescopeProcess:
    """Manages the gamescope process lifecycle."""

    # Marker in gamescope output that indicates it's fully initialized
    READY_MARKER = "Post-Initted Wayland backend"
    # Fallback timeout (seconds) if marker is not detected
    READY_TIMEOUT = 2.0

    def __init__(self, config: Config):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._stopping = False
        self._ready_fired = False
        self._ready_timeout_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_started: Optional[Callable[[], None]] = None
        self.on_stopped: Optional[Callable[[int], None]] = None
        self.on_output: Optional[Callable[[str], None]] = None
        self.on_ready: Optional[Callable[[], None]] = None

    @property
    def is_running(self) -> bool:
        """Check if gamescope is currently running."""
        return self._process is not None and self._process.returncode is None

    async def start(self, command: Optional[list[str]] = None):
        """Start gamescope with the configured settings."""
        if self.is_running:
            self._log("Gamescope is already running\n")
            return

        self._stopping = False
        self._ready_fired = False
        args = self.config.build_gamescope_args(command)

        self._log(f"Starting: {' '.join(args)}\n")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True  # Create new process group for signal handling
            )

            if self.on_started:
                self.on_started()

            # Start fallback ready timeout
            self._ready_timeout_task = asyncio.create_task(self._ready_timeout())

            # Start reading output
            asyncio.create_task(self._read_output())

            # Wait for process to exit
            exit_code = await self._process.wait()
            self._process = None

            self._log(f"Gamescope exited with code {exit_code}\n")

            if self.on_stopped:
                self.on_stopped(exit_code)

        except Exception as e:
            self._log(f"Failed to start gamescope: {e}\n")
            self._process = None
            if self.on_stopped:
                self.on_stopped(-1)

    async def stop(self):
        """Stop gamescope gracefully."""
        if not self.is_running:
            return

        self._stopping = True
        self._log("Stopping gamescope...\n")

        # Cancel ready timeout if pending
        if self._ready_timeout_task and not self._ready_timeout_task.done():
            self._ready_timeout_task.cancel()

        # Send SIGTERM to entire process group (handles flatpak run wrapper)
        try:
            pgid = os.getpgid(self._process.pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            # Fallback to direct signal if process group not available
            self._process.send_signal(signal.SIGTERM)

        # Wait up to 3 seconds for graceful exit
        try:
            await asyncio.wait_for(self._process.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            self._log("Force killing gamescope...\n")
            try:
                pgid = os.getpgid(self._process.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                self._process.kill()
            await self._process.wait()

    async def _read_output(self):
        """Read output from the process."""
        if self._process is None or self._process.stdout is None:
            return

        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                self._log(text)

                # Check for ready marker
                if not self._ready_fired and self.READY_MARKER in text:
                    self._fire_ready()
            except Exception:
                break

    async def _ready_timeout(self):
        """Fallback timer to fire ready callback if marker not detected."""
        try:
            await asyncio.sleep(self.READY_TIMEOUT)
            if not self._ready_fired and self.is_running:
                self._log(f"Ready timeout ({self.READY_TIMEOUT}s) - assuming ready\n")
                self._fire_ready()
        except asyncio.CancelledError:
            pass

    def _fire_ready(self):
        """Fire the on_ready callback once."""
        if self._ready_fired:
            return
        self._ready_fired = True

        # Cancel timeout task if still pending
        if self._ready_timeout_task and not self._ready_timeout_task.done():
            self._ready_timeout_task.cancel()

        if self.on_ready:
            self.on_ready()

    def _log(self, text: str):
        """Log a message."""
        if self.on_output:
            self.on_output(text)
