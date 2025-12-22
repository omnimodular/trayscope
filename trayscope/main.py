#!/usr/bin/env python3
"""Trayscope - System tray application for gamescope management."""

import sys
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio

from trayscope.config import Config
from trayscope.settings import SettingsDialog
from trayscope.log_viewer import LogViewer
from trayscope.gamescope import GamescopeManager
from trayscope.status_notifier import StatusNotifierItem


class TrayscopeApp(Gtk.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id='sh.ironforge.trayscope',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.config = None
        self.gamescope = None
        self.status_notifier = None
        self.settings_dialog = None
        self.log_viewer = None
        self.hold_count = 0

    def do_activate(self):
        """Called when the application is activated."""
        # Keep app running without a window
        if self.hold_count == 0:
            self.hold()
            self.hold_count += 1

    def do_startup(self):
        """Called when the application starts."""
        Gtk.Application.do_startup(self)

        self.config = Config()
        self.gamescope = GamescopeManager(self.config)

        # Connect gamescope signals
        self.gamescope.connect('started', self._on_gamescope_started)
        self.gamescope.connect('stopped', self._on_gamescope_stopped)
        self.gamescope.connect('log-output', self._on_log_output)

        # Create status notifier (system tray)
        self.status_notifier = StatusNotifierItem(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_settings=self._on_settings,
            on_logs=self._on_logs,
            on_quit=self._on_quit
        )
        self.status_notifier.register()

    def _on_start(self):
        """Start gamescope."""
        self.gamescope.start()

    def _on_stop(self):
        """Stop gamescope."""
        self.gamescope.stop()

    def _on_settings(self):
        """Open settings dialog."""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.config)
            self.settings_dialog.connect('destroy', self._on_settings_closed)
        self.settings_dialog.present()

    def _on_settings_closed(self, dialog):
        """Handle settings dialog closed."""
        self.settings_dialog = None

    def _on_logs(self):
        """Open log viewer."""
        if self.log_viewer is None:
            self.log_viewer = LogViewer()
            self.log_viewer.connect('destroy', self._on_logs_closed)
            # Add existing logs
            for line in self.gamescope.get_log_buffer():
                self.log_viewer.append_log(line)
        self.log_viewer.present()

    def _on_logs_closed(self, viewer):
        """Handle log viewer closed."""
        self.log_viewer = None

    def _on_quit(self):
        """Quit the application."""
        if self.gamescope.is_running():
            dialog = Gtk.MessageDialog(
                transient_for=None,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Gamescope is still running"
            )
            dialog.format_secondary_text("Stop it before quitting?")
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                self.gamescope.stop()

        self.status_notifier.unregister()
        self.quit()

    def _on_gamescope_started(self, manager):
        """Handle gamescope started."""
        self.status_notifier.set_status('active')
        self._notify("Gamescope started")

    def _on_gamescope_stopped(self, manager, exit_code):
        """Handle gamescope stopped."""
        self.status_notifier.set_status('passive')
        if exit_code != 0:
            self._notify(f"Gamescope exited with code {exit_code}")

    def _on_log_output(self, manager, text):
        """Handle log output."""
        if self.log_viewer is not None:
            self.log_viewer.append_log(text)

    def _notify(self, message):
        """Send a desktop notification."""
        notification = Gio.Notification.new("Trayscope")
        notification.set_body(message)
        self.send_notification(None, notification)


def main():
    """Entry point."""
    # Handle SIGINT gracefully
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: Gtk.main_quit())

    app = TrayscopeApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
