# Trayscope

A system tray application for managing [gamescope](https://github.com/ValveSoftware/gamescope), the SteamOS session compositing window manager.

Uses StatusNotifier D-Bus protocol for native Wayland support with waybar and other StatusNotifier-compatible bars.

## Features

- **System tray integration**: Start/stop gamescope from your desktop's system tray (waybar, KDE, etc.)
- **Pure Python**: No GTK/Qt dependencies, just D-Bus
- **Auto-restart**: Optionally restart gamescope on crash
- **Configurable**: Edit `~/.config/trayscope/config.json` to customize gamescope options

## Installation

```sh
pip install dbus-next
pip install .
```

## Usage

```sh
trayscope
```

The app will appear in your system tray (waybar tray module, KDE system tray, etc.).

## Configuration

Settings are saved to `~/.config/trayscope/config.json`:

```json
{
  "render_width": 1920,
  "render_height": 1080,
  "output_width": 0,
  "output_height": 0,
  "refresh_rate": 60,
  "filter": "fsr",
  "fullscreen": true,
  "backend": "wayland",
  "force_grab_cursor": true,
  "hdr_enabled": false,
  "adaptive_sync": false,
  "extra_args": "",
  "auto_restart": true
}
```

Set `output_width`/`output_height` to 0 for native resolution.

## Requirements

- Python 3.10+
- dbus-next
- A StatusNotifier-compatible system tray (waybar, KDE Plasma, GNOME with AppIndicator extension)
- gamescope (must be installed separately)

## License

BSD 2-Clause License. See [LICENSE](LICENSE) for details.

Copyright (c) 2025, Omnimodular AB
