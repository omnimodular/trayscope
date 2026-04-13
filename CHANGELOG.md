# Changelog

## [0.3.4] - 2026-04-13

### Fixed
- Closing the gamescope window (or any non-Stop exit) no longer takes the tray down with it; trayscope stays alive on the host session bus so the user can recover from the tray
- Gamescope sessions are now auto-restarted on unexpected exits (window close, crash, external kill), with a 3s minimum-uptime crash-loop guard; an explicit Stop from the tray menu always wins

## [0.3.3] - 2026-04-13

### Fixed
- Tray process lingering after gamescope crashed or the D-Bus session bus disconnected
- Transient StatusNotifierWatcher restarts (waybar reload, etc.) now re-register instead of treating the tray attachment as lost
- Gamescope spawn failures (missing binary, misconfigured command) no longer exit the tray, so the user can fix settings and retry

## [0.3.2] - 2026-04-05

### Added
- Single instance enforcement via D-Bus name ownership

## [0.3.1] - 2025-12-24

### Fixed
- Settings not graying out when gamescope starts

## [0.3.0] - 2025-12-24

### Added
- "Automatic" backend option as default (lets gamescope auto-detect)

### Fixed
- Autostart toggle losing gamescope running state
- Autostart not showing correct state at launch

### Changed
- All settings disabled when gamescope is running

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
