"""Gamescope process management using asyncio."""

import asyncio
import signal
from typing import Callable, Optional

from trayscope.config import Config


class GamescopeProcess:
    """Manages the gamescope process lifecycle."""

    def __init__(self, config: Config):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._stopping = False

        # Callbacks
        self.on_started: Optional[Callable[[], None]] = None
        self.on_stopped: Optional[Callable[[int], None]] = None
        self.on_output: Optional[Callable[[str], None]] = None

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
        args = self.config.build_gamescope_args(command)

        self._log(f"Starting: {' '.join(args)}\n")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            if self.on_started:
                self.on_started()

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

        # Send SIGTERM
        self._process.send_signal(signal.SIGTERM)

        # Wait up to 3 seconds for graceful exit
        try:
            await asyncio.wait_for(self._process.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            self._log("Force killing gamescope...\n")
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
            except Exception:
                break

    def _log(self, text: str):
        """Log a message."""
        if self.on_output:
            self.on_output(text)
