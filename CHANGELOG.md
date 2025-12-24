# Changelog

## [0.2.2] - 2025-12-24

### Changed
- Include SVG icons in wheel package for simpler distribution

## [0.2.1] - 2025-01-24

### Added
- Tray menu controls for refresh rate (60/120/144 Hz)
- Tray menu controls for backend (Wayland/X11)
- Tray menu toggles for fullscreen, grab cursor, and autostart

### Removed
- `auto_restart` feature

## [0.2.0] - 2025-01-24

### Changed
- Replaced `autorun_command` with simpler `autostart` boolean setting

## [0.1.1] - 2025-01-24

### Changed
- Use `XDG_CONFIG_HOME` for config path (defaults to `~/.config/trayscope`)

## [0.1.0] - 2025-01-24

### Added
- Initial release
- System tray integration via StatusNotifier D-Bus protocol
- Pure Python implementation using dbus-next (no GTK/Qt)
- Dynamic tray icon (green when gamescope running, red when stopped)
- Tray menu with start/stop controls
- Resolution submenu (720p, 1080p, 1440p, 4K)
- Filter submenu (FSR, Nearest, Linear)
- HDR and VRR toggles
- Configurable gamescope command for Flatpak support
- Auto-restart on crash option
- Autorun command execution when gamescope is ready
