"""Configuration management for Trayscope."""

import json
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GamescopeSettings:
    """Gamescope configuration settings."""
    # Resolution
    render_width: int = 1920
    render_height: int = 1080
    output_width: int = 0  # 0 = native/auto
    output_height: int = 0  # 0 = native/auto

    # Display
    refresh_rate: int = 60
    filter: str = "fsr"  # fsr, nearest, linear
    fullscreen: bool = True

    # Advanced
    backend: str = "auto"  # auto, wayland, x11
    force_grab_cursor: bool = True
    hdr_enabled: bool = False
    adaptive_sync: bool = False

    # Custom command (e.g., "flatpak run sh.ironforge.gamescope")
    # If empty, uses system gamescope binary
    gamescope_command: str = ""

    # Extra args (appended to gamescope command)
    extra_args: str = ""

    # Start gamescope automatically when trayscope starts
    autostart: bool = False


class Config:
    """Configuration manager for loading/saving settings."""

    CONFIG_DIR = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / "trayscope"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def __init__(self):
        self.settings = GamescopeSettings()
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Ensure the configuration directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Load settings from the config file."""
        if not self.CONFIG_FILE.exists():
            return

        try:
            with open(self.CONFIG_FILE, "r") as f:
                data = json.load(f)
            # Update settings with loaded values
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config: {e}")

    def save(self):
        """Save settings to the config file."""
        try:
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(asdict(self.settings), f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to save config: {e}")

    def get_native_resolution(self) -> tuple[int, int]:
        """Get native resolution using wlr-randr."""
        try:
            import subprocess
            result = subprocess.run(
                ["wlr-randr"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.splitlines():
                if "current" in line:
                    # Parse resolution from line like "  1920x1080 px, 60.000000 Hz (current)"
                    import re
                    match = re.search(r'(\d+)x(\d+)', line)
                    if match:
                        return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return 1920, 1080  # Fallback

    def get_gamescope_path(self) -> str:
        """Get the path to the gamescope binary."""
        # Check common locations
        candidates = [
            "/app/bin/gamescope",  # Flatpak
            "/usr/bin/gamescope",  # System
            "/usr/local/bin/gamescope",  # Local install
        ]
        for path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        # Fallback to PATH lookup
        path = shutil.which("gamescope")
        return path if path else "gamescope"

    def build_gamescope_args(self, command: Optional[list[str]] = None) -> list[str]:
        """Build gamescope command-line arguments from settings."""
        s = self.settings

        # Use custom command if specified, otherwise find gamescope binary
        if s.gamescope_command.strip():
            # Split custom command (e.g., "flatpak run sh.ironforge.gamescope")
            args = s.gamescope_command.strip().split()
        else:
            args = [self.get_gamescope_path()]

        if s.backend != "auto":
            args.extend([f"--backend={s.backend}"])

        if s.fullscreen:
            args.append("-f")

        if s.force_grab_cursor:
            args.append("--force-grab-cursor")

        args.extend(["-w", str(s.render_width)])
        args.extend(["-h", str(s.render_height)])

        # Output resolution
        out_w = s.output_width
        out_h = s.output_height
        if out_w <= 0 or out_h <= 0:
            out_w, out_h = self.get_native_resolution()
        args.extend(["-W", str(out_w)])
        args.extend(["-H", str(out_h)])

        args.extend(["-r", str(s.refresh_rate)])

        if s.filter:
            args.extend(["--filter", s.filter])

        if s.hdr_enabled:
            args.append("--hdr-enabled")

        if s.adaptive_sync:
            args.append("--adaptive-sync")

        # Extra args (split by whitespace)
        if s.extra_args.strip():
            args.extend(s.extra_args.strip().split())

        # Add separator and command if provided
        args.append("--")
        if command:
            args.extend(command)
        else:
            # Default: export DISPLAY to D-Bus and sleep
            # This lets other apps find the nested X server
            args.extend(["sh", "-c", "dbus-update-activation-environment DISPLAY; exec sleep infinity"])

        return args
