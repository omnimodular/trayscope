# Trayscope

A system tray application for managing [gamescope](https://github.com/ValveSoftware/gamescope), the SteamOS session compositing window manager.

Uses GTK3 and StatusNotifier D-Bus protocol for native Wayland support with waybar and other StatusNotifier-compatible bars.

## Features

- **System tray integration**: Start/stop gamescope from your desktop's system tray (waybar, KDE, etc.)
- **Settings UI**: Configure all gamescope options through a graphical interface
  - Render and output resolution
  - Refresh rate and upscale filter (FSR, nearest, linear)
  - HDR, VRR (Adaptive Sync), fullscreen mode
  - Backend (Wayland/X11), cursor grab
  - Custom command-line arguments
- **Log viewer**: Real-time view of gamescope output with copy/save/clear
- **Auto-restart**: Optionally restart gamescope on crash

## Installation

### System dependencies

Trayscope requires GTK3 and PyGObject:

```sh
# Arch Linux
pacman -S python-gobject gtk3

# Debian/Ubuntu
apt install python3-gi gir1.2-gtk-3.0

# Fedora
dnf install python3-gobject gtk3
```

### From source

```sh
git clone https://github.com/omnimodular/trayscope.git
cd trayscope
pip install .
```

## Usage

Run from the command line:

```sh
trayscope
```

The app will appear in your system tray (waybar tray module, KDE system tray, etc.).

## Configuration

Settings are saved to `~/.config/trayscope/config.json`.

## Requirements

- Python 3.10+
- GTK3
- PyGObject
- A StatusNotifier-compatible system tray (waybar, KDE Plasma, GNOME with AppIndicator extension)
- gamescope (must be installed separately)

## License

BSD 2-Clause License. See [LICENSE](LICENSE) for details.

Copyright (c) 2025, Omnimodular AB
