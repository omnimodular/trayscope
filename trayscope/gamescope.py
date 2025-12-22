"""Gamescope process management using GLib."""

from typing import Optional
from collections import deque

from gi.repository import GLib, GObject, Gio

from trayscope.config import Config


class GamescopeManager(GObject.Object):
    """Manages the gamescope process lifecycle."""

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'stopped': (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # exit_code
        'log-output': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    LOG_BUFFER_SIZE = 1000

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._process: Optional[Gio.Subprocess] = None
        self._stopping = False
        self._restart_source_id = None
        self._log_buffer = deque(maxlen=self.LOG_BUFFER_SIZE)

    def is_running(self) -> bool:
        """Check if gamescope is currently running."""
        return self._process is not None

    def get_log_buffer(self) -> list[str]:
        """Get the current log buffer contents."""
        return list(self._log_buffer)

    def start(self, command: Optional[list[str]] = None):
        """Start gamescope with the configured settings."""
        if self.is_running():
            self._log("Gamescope is already running\n")
            return

        self._stopping = False
        args = self.config.build_gamescope_args(command)

        self._log(f"Starting: {' '.join(args)}\n")

        try:
            # Create subprocess with pipes for stdout/stderr
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
            )

            self._process = launcher.spawnv(args)

            # Read stdout asynchronously
            stdout = self._process.get_stdout_pipe()
            self._read_output(stdout)

            # Watch for process exit
            self._process.wait_async(None, self._on_process_exit)

            self.emit('started')

        except GLib.Error as e:
            self._log(f"Failed to start gamescope: {e.message}\n")
            self._process = None

    def stop(self):
        """Stop gamescope gracefully."""
        if not self.is_running():
            return

        self._stopping = True

        # Cancel any pending restart
        if self._restart_source_id is not None:
            GLib.source_remove(self._restart_source_id)
            self._restart_source_id = None

        self._log("Stopping gamescope...\n")

        # Send SIGTERM
        self._process.send_signal(15)  # SIGTERM

        # Force kill after timeout
        GLib.timeout_add(3000, self._force_kill)

    def _force_kill(self):
        """Force kill if still running."""
        if self._process is not None:
            self._log("Force killing gamescope...\n")
            self._process.force_exit()
        return False  # Don't repeat

    def _read_output(self, stream):
        """Read output from the process asynchronously."""
        data_stream = Gio.DataInputStream.new(stream)
        data_stream.read_line_async(
            GLib.PRIORITY_DEFAULT,
            None,
            self._on_line_read,
            data_stream
        )

    def _on_line_read(self, stream, result, data_stream):
        """Handle a line read from the process."""
        try:
            line, length = stream.read_line_finish_utf8(result)
            if line is not None:
                self._log(line + "\n")
                # Continue reading
                data_stream.read_line_async(
                    GLib.PRIORITY_DEFAULT,
                    None,
                    self._on_line_read,
                    data_stream
                )
        except GLib.Error:
            # Stream closed or error
            pass

    def _on_process_exit(self, process, result):
        """Handle process exit."""
        try:
            process.wait_finish(result)
            exit_code = process.get_exit_status()
        except GLib.Error:
            exit_code = -1

        self._log(f"Gamescope exited with code {exit_code}\n")
        self._process = None
        self.emit('stopped', exit_code)

        # Auto-restart on crash if enabled and not manually stopped
        if (not self._stopping and
            self.config.settings.auto_restart and
            exit_code != 0):
            self._log("Will restart in 1 second...\n")
            self._restart_source_id = GLib.timeout_add(1000, self._do_restart)

    def _do_restart(self):
        """Perform auto-restart."""
        self._restart_source_id = None
        if not self._stopping:
            self._log("Auto-restarting gamescope...\n")
            self.start()
        return False  # Don't repeat

    def _log(self, text: str):
        """Log a message."""
        self._log_buffer.append(text)
        self.emit('log-output', text)
