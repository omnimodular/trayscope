"""Settings dialog for Trayscope."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from trayscope.config import Config


class SettingsDialog(Gtk.Window):
    """Settings dialog for configuring gamescope options."""

    def __init__(self, config: Config):
        super().__init__(title="Gamescope Settings")
        self.config = config
        self.set_default_size(450, 500)
        self.set_border_width(10)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the dialog UI."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Notebook for tabs
        notebook = Gtk.Notebook()
        vbox.pack_start(notebook, True, True, 0)

        notebook.append_page(self._create_resolution_tab(), Gtk.Label(label="Resolution"))
        notebook.append_page(self._create_display_tab(), Gtk.Label(label="Display"))
        notebook.append_page(self._create_advanced_tab(), Gtk.Label(label="Advanced"))

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        vbox.pack_start(button_box, False, False, 0)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.destroy())
        button_box.pack_start(cancel_btn, False, False, 0)

        save_btn = Gtk.Button(label="Save")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        button_box.pack_start(save_btn, False, False, 0)

        self.show_all()

    def _create_resolution_tab(self) -> Gtk.Widget:
        """Create the resolution settings tab."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        vbox.set_border_width(10)

        # Render resolution frame
        render_frame = Gtk.Frame(label="Render Resolution")
        render_grid = Gtk.Grid()
        render_grid.set_row_spacing(8)
        render_grid.set_column_spacing(10)
        render_grid.set_border_width(10)
        render_frame.add(render_grid)

        render_grid.attach(Gtk.Label(label="Width:", xalign=0), 0, 0, 1, 1)
        self.render_width = Gtk.SpinButton.new_with_range(640, 7680, 1)
        render_grid.attach(self.render_width, 1, 0, 1, 1)

        render_grid.attach(Gtk.Label(label="Height:", xalign=0), 0, 1, 1, 1)
        self.render_height = Gtk.SpinButton.new_with_range(480, 4320, 1)
        render_grid.attach(self.render_height, 1, 1, 1, 1)

        # Preset buttons
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        for name, w, h in [("720p", 1280, 720), ("1080p", 1920, 1080),
                           ("1440p", 2560, 1440), ("4K", 3840, 2160)]:
            btn = Gtk.Button(label=name)
            btn.connect("clicked", lambda b, w=w, h=h: self._set_render_preset(w, h))
            preset_box.pack_start(btn, True, True, 0)
        render_grid.attach(Gtk.Label(label="Presets:", xalign=0), 0, 2, 1, 1)
        render_grid.attach(preset_box, 1, 2, 1, 1)

        vbox.pack_start(render_frame, False, False, 0)

        # Output resolution frame
        output_frame = Gtk.Frame(label="Output Resolution")
        output_grid = Gtk.Grid()
        output_grid.set_row_spacing(8)
        output_grid.set_column_spacing(10)
        output_grid.set_border_width(10)
        output_frame.add(output_grid)

        output_grid.attach(Gtk.Label(label="Width:", xalign=0), 0, 0, 1, 1)
        self.output_width = Gtk.SpinButton.new_with_range(0, 7680, 1)
        self.output_width.set_tooltip_text("0 = Native resolution")
        output_grid.attach(self.output_width, 1, 0, 1, 1)

        output_grid.attach(Gtk.Label(label="Height:", xalign=0), 0, 1, 1, 1)
        self.output_height = Gtk.SpinButton.new_with_range(0, 4320, 1)
        self.output_height.set_tooltip_text("0 = Native resolution")
        output_grid.attach(self.output_height, 1, 1, 1, 1)

        detect_btn = Gtk.Button(label="Detect Native")
        detect_btn.connect("clicked", lambda b: self._detect_native_resolution())
        output_grid.attach(detect_btn, 1, 2, 1, 1)

        vbox.pack_start(output_frame, False, False, 0)

        return vbox

    def _create_display_tab(self) -> Gtk.Widget:
        """Create the display settings tab."""
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_border_width(10)

        row = 0

        grid.attach(Gtk.Label(label="Refresh Rate:", xalign=0), 0, row, 1, 1)
        self.refresh_rate = Gtk.SpinButton.new_with_range(30, 360, 1)
        grid.attach(self.refresh_rate, 1, row, 1, 1)
        grid.attach(Gtk.Label(label="Hz"), 2, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Upscale Filter:", xalign=0), 0, row, 1, 1)
        self.filter = Gtk.ComboBoxText()
        for f in ["fsr", "nearest", "linear"]:
            self.filter.append_text(f)
        grid.attach(self.filter, 1, row, 2, 1)
        row += 1

        filter_desc = Gtk.Label()
        filter_desc.set_markup(
            "<small>FSR: AMD FidelityFX (sharpened upscaling)\n"
            "Nearest: Pixel-perfect (best for retro)\n"
            "Linear: Smooth bilinear filtering</small>"
        )
        filter_desc.set_xalign(0)
        grid.attach(filter_desc, 0, row, 3, 1)
        row += 1

        self.fullscreen = Gtk.CheckButton(label="Fullscreen mode")
        grid.attach(self.fullscreen, 0, row, 3, 1)

        return grid

    def _create_advanced_tab(self) -> Gtk.Widget:
        """Create the advanced settings tab."""
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_border_width(10)

        row = 0

        grid.attach(Gtk.Label(label="Backend:", xalign=0), 0, row, 1, 1)
        self.backend = Gtk.ComboBoxText()
        for b in ["wayland", "x11"]:
            self.backend.append_text(b)
        grid.attach(self.backend, 1, row, 1, 1)
        row += 1

        self.force_grab_cursor = Gtk.CheckButton(label="Force grab cursor")
        grid.attach(self.force_grab_cursor, 0, row, 2, 1)
        row += 1

        self.hdr_enabled = Gtk.CheckButton(label="Enable HDR")
        grid.attach(self.hdr_enabled, 0, row, 2, 1)
        row += 1

        self.adaptive_sync = Gtk.CheckButton(label="Adaptive Sync (VRR)")
        grid.attach(self.adaptive_sync, 0, row, 2, 1)
        row += 1

        self.auto_restart = Gtk.CheckButton(label="Auto-restart on crash")
        grid.attach(self.auto_restart, 0, row, 2, 1)
        row += 1

        # Spacer
        grid.attach(Gtk.Label(), 0, row, 2, 1)
        row += 1

        grid.attach(Gtk.Label(label="Extra Arguments:", xalign=0), 0, row, 1, 1)
        self.extra_args = Gtk.Entry()
        self.extra_args.set_placeholder_text("e.g., --mangoapp --steam")
        self.extra_args.set_hexpand(True)
        grid.attach(self.extra_args, 1, row, 1, 1)
        row += 1

        extra_desc = Gtk.Label()
        extra_desc.set_markup(
            "<small>Additional command-line arguments passed to gamescope</small>"
        )
        extra_desc.set_xalign(0)
        grid.attach(extra_desc, 0, row, 2, 1)

        return grid

    def _set_render_preset(self, width: int, height: int):
        """Set render resolution to a preset value."""
        self.render_width.set_value(width)
        self.render_height.set_value(height)

    def _detect_native_resolution(self):
        """Detect and display the native resolution."""
        w, h = self.config.get_native_resolution()
        self.output_width.set_value(w)
        self.output_height.set_value(h)

    def _load_settings(self):
        """Load settings from config into the UI."""
        s = self.config.settings

        self.render_width.set_value(s.render_width)
        self.render_height.set_value(s.render_height)
        self.output_width.set_value(s.output_width)
        self.output_height.set_value(s.output_height)

        self.refresh_rate.set_value(s.refresh_rate)
        self.filter.set_active(["fsr", "nearest", "linear"].index(s.filter))
        self.fullscreen.set_active(s.fullscreen)

        self.backend.set_active(["wayland", "x11"].index(s.backend))
        self.force_grab_cursor.set_active(s.force_grab_cursor)
        self.hdr_enabled.set_active(s.hdr_enabled)
        self.adaptive_sync.set_active(s.adaptive_sync)
        self.auto_restart.set_active(s.auto_restart)
        self.extra_args.set_text(s.extra_args)

    def _on_save(self, button):
        """Save settings from UI to config."""
        s = self.config.settings

        s.render_width = int(self.render_width.get_value())
        s.render_height = int(self.render_height.get_value())
        s.output_width = int(self.output_width.get_value())
        s.output_height = int(self.output_height.get_value())

        s.refresh_rate = int(self.refresh_rate.get_value())
        s.filter = self.filter.get_active_text()
        s.fullscreen = self.fullscreen.get_active()

        s.backend = self.backend.get_active_text()
        s.force_grab_cursor = self.force_grab_cursor.get_active()
        s.hdr_enabled = self.hdr_enabled.get_active()
        s.adaptive_sync = self.adaptive_sync.get_active()
        s.auto_restart = self.auto_restart.get_active()
        s.extra_args = self.extra_args.get_text()

        self.config.save()
        self.destroy()
