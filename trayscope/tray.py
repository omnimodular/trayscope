"""StatusNotifier D-Bus implementation using dbus-next."""

import os
from typing import Callable, Optional

from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property, signal, PropertyAccess
from dbus_next import Variant, BusType


def _make_crosshair_pixmap(active: bool):
    """Create a 22x22 ARGB crosshair icon. Green if active, red if inactive."""
    size = 22
    cx, cy = size // 2, size // 2
    pixels = []

    # Colors: green for active, red for inactive
    if active:
        color = (0x33, 0xFF, 0x55)  # Bright green
        glow = (0x00, 0xAA, 0x22)   # Darker green
    else:
        color = (0xFF, 0x33, 0x33)  # Bright red
        glow = (0xAA, 0x00, 0x00)   # Darker red

    for y in range(size):
        for x in range(size):
            dx, dy = abs(x - cx), abs(y - cy)
            dist = (dx * dx + dy * dy) ** 0.5

            # Lens background (dark circle)
            if dist <= 9:
                # Crosshair lines (vertical and horizontal through center)
                if (x == cx and dy <= 8) or (y == cy and dx <= 8):
                    a, r, g, b = 0xFF, *color
                # Center dot
                elif dist <= 1.5:
                    a, r, g, b = 0xFF, *color
                # Tick marks on crosshair
                elif (x == cx and dy in [3, 5, 7]) or (y == cy and dx in [3, 5, 7]):
                    a, r, g, b = 0xFF, *color
                # Dark lens interior
                else:
                    a, r, g, b = 0xDD, 0x1a, 0x1f, 0x24
            # Lens ring
            elif dist <= 10:
                a, r, g, b = 0xFF, 0x3c, 0x48, 0x52
            else:
                a, r, g, b = 0x00, 0x00, 0x00, 0x00

            pixels.extend([a, r, g, b])

    return [size, size, bytes(pixels)]


ICON_ACTIVE = _make_crosshair_pixmap(True)
ICON_INACTIVE = _make_crosshair_pixmap(False)


class StatusNotifierItemInterface(ServiceInterface):
    """org.kde.StatusNotifierItem D-Bus interface."""

    def __init__(self, service: "StatusNotifierService"):
        super().__init__("org.kde.StatusNotifierItem")
        self._service = service
        self._status = "Active"  # Always Active so icon is visible
        self._gamescope_running = False  # Track gamescope state for icon
        self._icon_name = "trayscope-inactive"

    @dbus_property(access=PropertyAccess.READ)
    def Category(self) -> "s":
        return "ApplicationStatus"

    @dbus_property(access=PropertyAccess.READ)
    def Id(self) -> "s":
        return "trayscope"

    @dbus_property(access=PropertyAccess.READ)
    def Title(self) -> "s":
        return "Trayscope"

    @dbus_property(access=PropertyAccess.READ)
    def Status(self) -> "s":
        return self._status

    @dbus_property(access=PropertyAccess.READ)
    def IconName(self) -> "s":
        return self._icon_name

    @dbus_property(access=PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        # Return green crosshair if running, red if not
        return [ICON_ACTIVE if self._gamescope_running else ICON_INACTIVE]

    @dbus_property(access=PropertyAccess.READ)
    def OverlayIconName(self) -> "s":
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def OverlayIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(access=PropertyAccess.READ)
    def AttentionIconName(self) -> "s":
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def AttentionIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(access=PropertyAccess.READ)
    def AttentionMovieName(self) -> "s":
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def IconThemePath(self) -> "s":
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def Menu(self) -> "o":
        return "/MenuBar"

    @dbus_property(access=PropertyAccess.READ)
    def ItemIsMenu(self) -> "b":
        return False  # Like Telegram

    @dbus_property(access=PropertyAccess.READ)
    def ToolTip(self) -> "(sa(iiay)ss)":
        return ["", [], "Trayscope", "Gamescope launcher"]

    @dbus_property(access=PropertyAccess.READ)
    def WindowId(self) -> "i":
        return 0

    @method()
    def Activate(self, x: "i", y: "i"):
        print(f"Activate called at {x},{y}")

    @method()
    def SecondaryActivate(self, x: "i", y: "i"):
        print(f"SecondaryActivate called at {x},{y}")

    @method()
    def ContextMenu(self, x: "i", y: "i"):
        print(f"ContextMenu called at {x},{y}")

    @method()
    def Scroll(self, delta: "i", orientation: "s"):
        pass

    @method()
    def ProvideXdgActivationToken(self, token: "s"):
        pass

    @signal()
    def NewStatus(self) -> "s":
        return self._status

    @signal()
    def NewIcon(self) -> "":
        return None

    @signal()
    def NewTitle(self) -> "":
        return None

    @signal()
    def NewToolTip(self) -> "":
        return None

    @signal()
    def NewMenu(self) -> "":
        return None

    def set_gamescope_running(self, running: bool):
        """Update icon based on gamescope state."""
        self._gamescope_running = running
        self._icon_name = "trayscope-active" if running else "trayscope-inactive"
        self.NewIcon()


class DBusMenuInterface(ServiceInterface):
    """com.canonical.dbusmenu D-Bus interface."""

    def __init__(self, service: "StatusNotifierService"):
        super().__init__("com.canonical.dbusmenu")
        self._service = service
        self._revision = 1

    @dbus_property(access=PropertyAccess.READ)
    def Version(self) -> "u":
        return 3

    @dbus_property(access=PropertyAccess.READ)
    def Status(self) -> "s":
        return "normal"

    @dbus_property(access=PropertyAccess.READ)
    def TextDirection(self) -> "s":
        return "ltr"

    @dbus_property(access=PropertyAccess.READ)
    def IconThemePath(self) -> "as":
        return []

    @method()
    def GetLayout(self, parent_id: "i", recursion_depth: "i",
                  property_names: "as") -> "u(ia{sv}av)":
        layout = self._build_layout(parent_id, recursion_depth)
        return [self._revision, layout]

    @method()
    def GetGroupProperties(self, ids: "ai", property_names: "as") -> "a(ia{sv})":
        result = []
        for item_id in ids:
            props = self._get_item_props(item_id)
            result.append([item_id, props])
        return result

    @method()
    def GetProperty(self, id_: "i", name: "s") -> "v":
        props = self._get_item_props(id_)
        return props.get(name, Variant("s", ""))

    @method()
    def Event(self, id_: "i", event_id: "s", data: "v", timestamp: "u"):
        print(f"Menu Event: id={id_}, event={event_id}")
        if event_id == "clicked":
            self._service._handle_click(id_)

    @method()
    def EventGroup(self, events: "a(isvu)") -> "ai":
        for id_, event_id, data, timestamp in events:
            if event_id == "clicked":
                self._service._handle_click(id_)
        return []

    @method()
    def AboutToShow(self, id_: "i") -> "b":
        return False

    @method()
    def AboutToShowGroup(self, ids: "ai") -> "aiai":
        return [[], []]

    @signal()
    def LayoutUpdated(self) -> "ui":
        return [self._revision, 0]

    @signal()
    def ItemsPropertiesUpdated(self) -> "a(ia{sv})a(ias)":
        return [[], []]

    def _build_layout(self, parent_id: int, depth: int = -1):
        if parent_id == 0:
            # Root menu
            children = []
            if depth != 0:
                for item_id in self._service._root_items:
                    child = self._build_layout(item_id, depth - 1 if depth > 0 else -1)
                    children.append(Variant("(ia{sv}av)", child))
            return [0, {"children-display": Variant("s", "submenu")}, children]
        else:
            item = self._service._menu_items.get(parent_id)
            props = self._get_item_props(parent_id)
            children = []
            # Check for submenu children (6th element)
            if item and len(item) > 5 and item[5]:
                if depth != 0:
                    for child_id in item[5]:
                        child = self._build_layout(child_id, depth - 1 if depth > 0 else -1)
                        children.append(Variant("(ia{sv}av)", child))
            return [parent_id, props, children]

    def _get_item_props(self, item_id: int) -> dict:
        items = self._service._menu_items
        if item_id not in items:
            return {}

        item = items[item_id]
        # Format: (label, callback, enabled, toggle_type, toggle_state, children)
        label = item[0]
        enabled = item[2] if len(item) > 2 else True
        toggle_type = item[3] if len(item) > 3 else None
        toggle_state = item[4] if len(item) > 4 else None
        children = item[5] if len(item) > 5 else None

        if label == "separator":
            return {"type": Variant("s", "separator")}

        props = {
            "label": Variant("s", label),
            "enabled": Variant("b", enabled),
            "visible": Variant("b", True),
        }

        # Submenu indicator
        if children:
            props["children-display"] = Variant("s", "submenu")

        # Toggle type and state
        if toggle_type:
            props["toggle-type"] = Variant("s", toggle_type)
            props["toggle-state"] = Variant("i", 1 if toggle_state else 0)

        return props

    def notify_layout_update(self):
        self._revision += 1
        self.LayoutUpdated()


class StatusNotifierService:
    """StatusNotifier service for system tray integration."""

    WATCHER_BUS = "org.kde.StatusNotifierWatcher"
    WATCHER_PATH = "/StatusNotifierWatcher"

    def __init__(self, on_start: Optional[Callable] = None,
                 on_stop: Optional[Callable] = None,
                 on_quit: Optional[Callable] = None):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_quit = on_quit

        self._bus: Optional[MessageBus] = None
        self._unique_name: str = ""

        self._sni_interface = StatusNotifierItemInterface(self)
        self._menu_interface = DBusMenuInterface(self)

        # Track gamescope running state for menu rebuilding
        self._gamescope_running = False

        # Menu structure
        # id -> (label, callback, enabled, children_ids)
        # children_ids is None for leaf items, list of ids for submenus
        self._menu_items = {}
        self._rebuild_menu()

    def _rebuild_menu(self):
        """Build menu with submenus for grouping."""
        s = self._config.settings if hasattr(self, '_config') and self._config else None
        cur_res = (s.render_width, s.render_height) if s else (1920, 1080)
        cur_filter = s.filter if s else "fsr"
        cur_refresh = s.refresh_rate if s else 60
        cur_backend = s.backend if s else "wayland"
        hdr_on = s.hdr_enabled if s else False
        vrr_on = s.adaptive_sync if s else False
        fullscreen_on = s.fullscreen if s else True
        grab_on = s.force_grab_cursor if s else True
        autostart_on = s.autostart if s else False

        # Use visual markers since waybar may not render toggle indicators
        def mark(label, selected):
            return f"● {label}" if selected else f"○ {label}"

        def check(label, on):
            return f"✓ {label}" if on else f"  {label}"

        # Use tracked running state for Start/Stop enabled status
        running = self._gamescope_running

        # Format: (label, callback, enabled, toggle_type, toggle_state, children)
        self._menu_items = {
            1: ("Start Gamescope", self._do_start, not running, None, None, None),
            2: ("Stop Gamescope", self._do_stop, running, None, None, None),
            3: ("separator", None, True, None, None, None),
            # Resolution submenu (disabled when running)
            10: ("Resolution", None, not running, None, None, [11, 12, 13, 14]),
            11: (mark("720p", cur_res == (1280, 720)), lambda: self._set_resolution(1280, 720), not running, "radio", cur_res == (1280, 720), None),
            12: (mark("1080p", cur_res == (1920, 1080)), lambda: self._set_resolution(1920, 1080), not running, "radio", cur_res == (1920, 1080), None),
            13: (mark("1440p", cur_res == (2560, 1440)), lambda: self._set_resolution(2560, 1440), not running, "radio", cur_res == (2560, 1440), None),
            14: (mark("4K", cur_res == (3840, 2160)), lambda: self._set_resolution(3840, 2160), not running, "radio", cur_res == (3840, 2160), None),
            # Refresh Rate submenu (disabled when running)
            50: ("Refresh Rate", None, not running, None, None, [51, 52, 53]),
            51: (mark("60 Hz", cur_refresh == 60), lambda: self._set_refresh_rate(60), not running, "radio", cur_refresh == 60, None),
            52: (mark("120 Hz", cur_refresh == 120), lambda: self._set_refresh_rate(120), not running, "radio", cur_refresh == 120, None),
            53: (mark("144 Hz", cur_refresh == 144), lambda: self._set_refresh_rate(144), not running, "radio", cur_refresh == 144, None),
            # Filter submenu (disabled when running)
            20: ("Filter", None, not running, None, None, [21, 22, 23]),
            21: (mark("FSR", cur_filter == "fsr"), lambda: self._set_filter("fsr"), not running, "radio", cur_filter == "fsr", None),
            22: (mark("Nearest", cur_filter == "nearest"), lambda: self._set_filter("nearest"), not running, "radio", cur_filter == "nearest", None),
            23: (mark("Linear", cur_filter == "linear"), lambda: self._set_filter("linear"), not running, "radio", cur_filter == "linear", None),
            # Backend submenu (disabled when running)
            60: ("Backend", None, not running, None, None, [61, 62, 63]),
            61: (mark("Automatic", cur_backend == "auto"), lambda: self._set_backend("auto"), not running, "radio", cur_backend == "auto", None),
            62: (mark("Wayland", cur_backend == "wayland"), lambda: self._set_backend("wayland"), not running, "radio", cur_backend == "wayland", None),
            63: (mark("X11", cur_backend == "x11"), lambda: self._set_backend("x11"), not running, "radio", cur_backend == "x11", None),
            # Toggles (disabled when running)
            30: ("separator", None, True, None, None, None),
            31: (check("HDR", hdr_on), self._toggle_hdr, not running, "checkmark", hdr_on, None),
            32: (check("VRR", vrr_on), self._toggle_vrr, not running, "checkmark", vrr_on, None),
            33: (check("Fullscreen", fullscreen_on), self._toggle_fullscreen, not running, "checkmark", fullscreen_on, None),
            34: (check("Grab Cursor", grab_on), self._toggle_grab_cursor, not running, "checkmark", grab_on, None),
            35: (check("Autostart", autostart_on), self._toggle_autostart, not running, "checkmark", autostart_on, None),
            # Quit
            40: ("separator", None, True, None, None, None),
            41: ("Quit", self._do_quit, True, None, None, None),
        }
        self._root_items = [1, 2, 3, 10, 50, 20, 60, 30, 31, 32, 33, 34, 35, 40, 41]

    async def connect(self):
        """Connect to D-Bus and register interfaces."""
        self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        self._unique_name = self._bus.unique_name

        # Export interfaces
        self._bus.export("/StatusNotifierItem", self._sni_interface)
        self._bus.export("/MenuBar", self._menu_interface)

        print(f"D-Bus unique name: {self._unique_name}")

        # Register with StatusNotifierWatcher using unique name (like Telegram does)
        try:
            introspection = await self._bus.introspect(
                self.WATCHER_BUS, self.WATCHER_PATH
            )
            proxy = self._bus.get_proxy_object(
                self.WATCHER_BUS, self.WATCHER_PATH, introspection
            )
            watcher = proxy.get_interface("org.kde.StatusNotifierWatcher")
            # Register with just the unique bus name - watcher adds the path
            await watcher.call_register_status_notifier_item(self._unique_name)
            print("Registered with StatusNotifierWatcher")
        except Exception as e:
            print(f"Warning: Could not register: {e}")

    async def disconnect(self):
        if self._bus:
            self._bus.disconnect()
            self._bus = None

    async def set_gamescope_running(self, running: bool):
        """Update tray state based on whether gamescope is running."""
        self._gamescope_running = running
        # Rebuild entire menu to update enabled state of all settings
        self._rebuild_menu()
        # Keep SNI Status always "Active" so icon remains visible
        # Only update the icon color (green=running, red=stopped)
        self._sni_interface.set_gamescope_running(running)
        self._menu_interface.notify_layout_update()

    def _handle_click(self, item_id: int):
        print(f"Menu click: item {item_id}")
        if item_id in self._menu_items:
            item = self._menu_items[item_id]
            label, callback, enabled = item[0], item[1], item[2]
            if callback and enabled:
                callback()

    def _do_start(self):
        print("Action: Start")
        if self.on_start:
            self.on_start()

    def _do_stop(self):
        print("Action: Stop")
        if self.on_stop:
            self.on_stop()

    def _do_quit(self):
        print("Action: Quit")
        if self.on_quit:
            self.on_quit()

    def set_config(self, config):
        """Set the config object for saving settings."""
        self._config = config
        # Rebuild menu to reflect config values (e.g., autostart state)
        self._rebuild_menu()

    def _set_resolution(self, width: int, height: int):
        print(f"Setting resolution: {width}x{height}")
        if hasattr(self, '_config') and self._config:
            self._config.settings.render_width = width
            self._config.settings.render_height = height
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _set_filter(self, filter_name: str):
        print(f"Setting filter: {filter_name}")
        if hasattr(self, '_config') and self._config:
            self._config.settings.filter = filter_name
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _toggle_hdr(self):
        if hasattr(self, '_config') and self._config:
            self._config.settings.hdr_enabled = not self._config.settings.hdr_enabled
            print(f"HDR: {self._config.settings.hdr_enabled}")
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _toggle_vrr(self):
        if hasattr(self, '_config') and self._config:
            self._config.settings.adaptive_sync = not self._config.settings.adaptive_sync
            print(f"VRR: {self._config.settings.adaptive_sync}")
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _toggle_fullscreen(self):
        if hasattr(self, '_config') and self._config:
            self._config.settings.fullscreen = not self._config.settings.fullscreen
            print(f"Fullscreen: {self._config.settings.fullscreen}")
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _toggle_grab_cursor(self):
        if hasattr(self, '_config') and self._config:
            self._config.settings.force_grab_cursor = not self._config.settings.force_grab_cursor
            print(f"Grab Cursor: {self._config.settings.force_grab_cursor}")
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _toggle_autostart(self):
        if hasattr(self, '_config') and self._config:
            self._config.settings.autostart = not self._config.settings.autostart
            print(f"Autostart: {self._config.settings.autostart}")
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _set_refresh_rate(self, hz: int):
        print(f"Setting refresh rate: {hz} Hz")
        if hasattr(self, '_config') and self._config:
            self._config.settings.refresh_rate = hz
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()

    def _set_backend(self, backend: str):
        print(f"Setting backend: {backend}")
        if hasattr(self, '_config') and self._config:
            self._config.settings.backend = backend
            self._config.save()
            self._rebuild_menu()
            self._menu_interface.notify_layout_update()
