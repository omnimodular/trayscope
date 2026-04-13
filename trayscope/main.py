#!/usr/bin/env python3
"""Trayscope - System tray for gamescope."""

import asyncio
import signal
import sys
import time
from typing import Optional

from trayscope.config import Config
from trayscope.tray import SingleInstanceError, StatusNotifierService
from trayscope.process import GamescopeProcess


class Trayscope:
    # Don't auto-restart gamescope if it exits this quickly after starting —
    # avoids a tight loop when the launch command is misconfigured or the
    # environment is broken in a way that kills gamescope at startup.
    MIN_UPTIME_FOR_AUTO_RESTART = 3.0

    def __init__(self):
        self.config = Config()
        self.process = GamescopeProcess(self.config)
        self.tray = None
        self._running = True
        self._gamescope_start_time: Optional[float] = None
        # Session intent: True between Start (user or autostart) and an
        # explicit Stop. Drives auto-restart on unexpected gamescope exits.
        self._session_active = False

    async def run(self):
        self.tray = StatusNotifierService(
            on_start=self.start_gamescope,
            on_stop=self.stop_gamescope,
            on_quit=self.quit,
            on_lost=self._on_tray_lost,
        )

        self.process.on_started = self._on_started
        self.process.on_stopped = self._on_stopped
        self.process.on_output = self._on_output

        self.tray.set_config(self.config)
        await self.tray.connect()
        print("Trayscope running.")

        if self.config.settings.autostart:
            print("Autostart enabled, starting gamescope...")
            self.start_gamescope()

        while self._running:
            await asyncio.sleep(0.1)

        await self.cleanup()

    def start_gamescope(self):
        if not self.process.is_running:
            self._session_active = True
            asyncio.create_task(self.process.start())

    def stop_gamescope(self):
        if self.process.is_running:
            self._session_active = False
            asyncio.create_task(self.process.stop())

    def quit(self):
        self._running = False

    def _on_started(self):
        self._gamescope_start_time = time.monotonic()
        if self.tray:
            asyncio.create_task(self.tray.set_gamescope_running(True))

    def _on_stopped(self, exit_code: int, user_initiated: bool):
        if self.tray:
            asyncio.create_task(self.tray.set_gamescope_running(False))
        if user_initiated:
            # Explicit Stop via the tray menu — keep gamescope stopped.
            return
        if not self._session_active:
            # No active session (e.g., Stop was already requested, or the
            # process exited before a session was ever established).
            print(f"Gamescope exited on its own (code {exit_code}); tray staying alive.")
            return
        # Unexpected exit during an active session (window closed, crash,
        # external kill). Auto-restart so the session persists until the
        # user explicitly stops it. Crash-loop guard: skip if uptime was
        # too short — a misconfigured launch shouldn't spin forever.
        started = self._gamescope_start_time
        ran_for = (time.monotonic() - started) if started is not None else 0.0
        if ran_for < self.MIN_UPTIME_FOR_AUTO_RESTART:
            self._session_active = False
            print(
                f"Gamescope exited after {ran_for:.1f}s (code {exit_code}); "
                f"not auto-restarting (ran <{self.MIN_UPTIME_FOR_AUTO_RESTART}s, "
                f"avoiding tight loop)."
            )
            return
        print(
            f"Gamescope exited after {ran_for:.1f}s (code {exit_code}); "
            f"auto-restarting."
        )
        self.start_gamescope()

    def _on_tray_lost(self):
        # D-Bus tray attachment is gone (bus disconnect or watcher vanished).
        # Nothing left to drive the UI, so exit.
        self.quit()

    def _on_output(self, line: str):
        print(f"[gs] {line}", end="")

    async def cleanup(self):
        if self.process.is_running:
            await self.process.stop()
        if self.tray:
            await self.tray.disconnect()


def main():
    app = Trayscope()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, app.quit)

    try:
        loop.run_until_complete(app.run())
    except KeyboardInterrupt:
        pass
    except SingleInstanceError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
