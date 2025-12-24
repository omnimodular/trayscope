#!/usr/bin/env python3
"""Trayscope - System tray for gamescope."""

import asyncio
import signal
import sys

from trayscope.config import Config
from trayscope.tray import StatusNotifierService
from trayscope.process import GamescopeProcess


class Trayscope:
    def __init__(self):
        self.config = Config()
        self.process = GamescopeProcess(self.config)
        self.tray = None
        self._running = True

    async def run(self):
        self.tray = StatusNotifierService(
            on_start=self.start_gamescope,
            on_stop=self.stop_gamescope,
            on_quit=self.quit
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
            asyncio.create_task(self.process.start())

    def stop_gamescope(self):
        if self.process.is_running:
            asyncio.create_task(self.process.stop())

    def quit(self):
        self._running = False

    def _on_started(self):
        if self.tray:
            asyncio.create_task(self.tray.set_gamescope_running(True))

    def _on_stopped(self, exit_code: int):
        if self.tray:
            asyncio.create_task(self.tray.set_gamescope_running(False))

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
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
