"""Log viewer window for Trayscope."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango


class LogViewer(Gtk.Window):
    """Window for viewing gamescope log output."""

    MAX_LINES = 10000

    def __init__(self):
        super().__init__(title="Gamescope Logs")
        self.set_default_size(700, 500)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the log viewer UI."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_border_width(5)
        self.add(vbox)

        # Scrolled window with text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        vbox.pack_start(scrolled, True, True, 0)

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.set_monospace(True)
        scrolled.add(self.text_view)

        self.text_buffer = self.text_view.get_buffer()

        # Button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.pack_start(button_box, False, False, 0)

        self.auto_scroll = Gtk.CheckButton(label="Auto-scroll")
        self.auto_scroll.set_active(True)
        button_box.pack_start(self.auto_scroll, False, False, 0)

        button_box.pack_start(Gtk.Box(), True, True, 0)  # Spacer

        copy_btn = Gtk.Button(label="Copy All")
        copy_btn.connect("clicked", self._on_copy_all)
        button_box.pack_start(copy_btn, False, False, 0)

        save_btn = Gtk.Button(label="Save...")
        save_btn.connect("clicked", self._on_save)
        button_box.pack_start(save_btn, False, False, 0)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", self._on_clear)
        button_box.pack_start(clear_btn, False, False, 0)

        self.show_all()

    def append_log(self, text: str):
        """Append text to the log output."""
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)

        # Limit lines
        line_count = self.text_buffer.get_line_count()
        if line_count > self.MAX_LINES:
            start = self.text_buffer.get_start_iter()
            delete_to = self.text_buffer.get_iter_at_line(line_count - self.MAX_LINES)
            self.text_buffer.delete(start, delete_to)

        # Auto-scroll if enabled
        if self.auto_scroll.get_active():
            end_iter = self.text_buffer.get_end_iter()
            self.text_view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)

    def _on_copy_all(self, button):
        """Copy all log text to clipboard."""
        start = self.text_buffer.get_start_iter()
        end = self.text_buffer.get_end_iter()
        text = self.text_buffer.get_text(start, end, False)

        if text:
            clipboard = Gtk.Clipboard.get_default(self.get_display())
            clipboard.set_text(text, -1)

    def _on_save(self, button):
        """Save logs to a file."""
        start = self.text_buffer.get_start_iter()
        end = self.text_buffer.get_end_iter()
        text = self.text_buffer.get_text(start, end, False)

        if not text:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No logs to save"
            )
            dialog.run()
            dialog.destroy()
            return

        file_dialog = Gtk.FileChooserDialog(
            title="Save Logs",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        file_dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT
        )
        file_dialog.set_current_name("gamescope.log")
        file_dialog.set_do_overwrite_confirmation(True)

        # Add filters
        filter_log = Gtk.FileFilter()
        filter_log.set_name("Log files")
        filter_log.add_pattern("*.log")
        file_dialog.add_filter(filter_log)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        file_dialog.add_filter(filter_all)

        response = file_dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = file_dialog.get_filename()
            try:
                with open(filename, "w") as f:
                    f.write(text)
            except IOError as e:
                error_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Failed to save logs"
                )
                error_dialog.format_secondary_text(str(e))
                error_dialog.run()
                error_dialog.destroy()

        file_dialog.destroy()

    def _on_clear(self, button):
        """Clear the log output."""
        self.text_buffer.set_text("")
