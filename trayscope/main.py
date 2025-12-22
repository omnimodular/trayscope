#!/usr/bin/env python3
"""Trayscope - System tray application for gamescope management.

Uses dbus-next for StatusNotifier protocol (pure Python, no GTK).
"""

import asyncio
import signal
import sys

from trayscope.config import Config
from trayscope.tray import StatusNotifierService
from trayscope.process import GamescopeProcess


class Trayscope:
    """Main application class."""

    def __init__(self):
        self.config = Config()
        self.process = GamescopeProcess(self.config)
        self.tray = None
        self._running = True

    async def run(self):
        """Run the application."""
        # Create and register tray
        self.tray = StatusNotifierService(
            on_start=self.start_gamescope,
            on_stop=self.stop_gamescope,
            on_quit=self.quit
        )

        # Connect process signals
        self.process.on_started = self._on_started
        self.process.on_stopped = self._on_stopped
        self.process.on_output = self._on_output

        await self.tray.connect()

        print("Trayscope running. Use system tray to control gamescope.")

        # Wait until quit
        while self._running:
            await asyncio.sleep(0.1)

        await self.cleanup()

    def start_gamescope(self):
        """Start gamescope."""
        if not self.process.is_running:
            asyncio.create_task(self.process.start())

    def stop_gamescope(self):
        """Stop gamescope."""
        if self.process.is_running:
            asyncio.create_task(self.process.stop())

    def quit(self):
        """Quit the application."""
        self._running = False

    def _on_started(self):
        """Handle gamescope started."""
        if self.tray:
            asyncio.create_task(self.tray.set_status("Active"))

    def _on_stopped(self, exit_code: int):
        """Handle gamescope stopped."""
        if self.tray:
            asyncio.create_task(self.tray.set_status("Passive"))
        if exit_code != 0 and self.config.settings.auto_restart and self._running:
            print(f"Gamescope crashed (exit {exit_code}), restarting in 1s...")
            asyncio.get_event_loop().call_later(1.0, self.start_gamescope)

    def _on_output(self, line: str):
        """Handle gamescope output."""
        print(f"[gamescope] {line}", end="")

    async def cleanup(self):
        """Clean up resources."""
        if self.process.is_running:
            await self.process.stop()
        if self.tray:
            await self.tray.disconnect()


def main():
    """Entry point."""
    app = Trayscope()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Handle SIGINT/SIGTERM
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, app.quit)

    try:
        loop.run_until_complete(app.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
