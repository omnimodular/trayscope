"""StatusNotifier D-Bus implementation using dbus-next (pure Python)."""

import os
from typing import Callable, Optional

from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property, signal, PropertyAccess
from dbus_next import Variant, BusType


def _make_icon_pixmap():
    """Create a simple 22x22 ARGB icon (green square)."""
    size = 22
    pixels = []
    for y in range(size):
        for x in range(size):
            cx, cy = size // 2, size // 2
            dx, dy = abs(x - cx), abs(y - cy)

            if dx <= 7 and dy <= 5:
                # Green: ARGB format (each pixel is 4 bytes)
                a, r, g, b = 0xFF, 0x00, 0xAA, 0x00
            elif dx <= 8 and dy <= 6:
                # Border
                a, r, g, b = 0xFF, 0x00, 0x77, 0x00
            else:
                a, r, g, b = 0x00, 0x00, 0x00, 0x00

            # ARGB in network byte order (big-endian)
            pixels.extend([a, r, g, b])

    return (size, size, bytes(pixels))


# Pre-generate icon
ICON_PIXMAP = _make_icon_pixmap()


class StatusNotifierItemInterface(ServiceInterface):
    """org.kde.StatusNotifierItem D-Bus interface."""

    def __init__(self, service: "StatusNotifierService"):
        super().__init__("org.kde.StatusNotifierItem")
        self._service = service
        self._status = "Passive"

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
        return ""  # Empty - we use IconPixmap instead

    @dbus_property(access=PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        # Array of [width, height, ARGB data] - must be lists for dbus-next
        w, h, data = ICON_PIXMAP
        return [[w, h, data]]

    @dbus_property(access=PropertyAccess.READ)
    def AttentionIconName(self) -> "s":
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def AttentionIconPixmap(self) -> "a(iiay)":
        w, h, data = ICON_PIXMAP
        return [[w, h, data]]

    @dbus_property(access=PropertyAccess.READ)
    def IconThemePath(self) -> "s":
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def Menu(self) -> "o":
        return "/MenuBar"

    @dbus_property(access=PropertyAccess.READ)
    def ItemIsMenu(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def ToolTip(self) -> "(sa(iiay)ss)":
        # [icon_name, icon_data, title, description] - must be list for dbus-next
        return ["", [], "Trayscope", "Gamescope launcher"]

    @method()
    def Activate(self, x: "i", y: "i"):
        pass

    @method()
    def SecondaryActivate(self, x: "i", y: "i"):
        pass

    @method()
    def ContextMenu(self, x: "i", y: "i"):
        pass

    @method()
    def Scroll(self, delta: "i", orientation: "s"):
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

    def update_status(self, status: str):
        """Update status and emit signal."""
        self._status = status
        self.NewStatus()


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
        if name in props:
            return props[name]
        return Variant("s", "")

    @method()
    def Event(self, id_: "i", event_id: "s", data: "v", timestamp: "u"):
        if event_id == "clicked":
            self._service._handle_click(id_)

    @method()
    def EventGroup(self, events: "a(isvu)") -> "ai":
        errors = []
        for id_, event_id, data, timestamp in events:
            if event_id == "clicked":
                self._service._handle_click(id_)
        return errors

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
        """Build menu layout."""
        if parent_id == 0:
            # Root menu
            children = []
            if depth != 0:
                for item_id in sorted(self._service._menu_items.keys()):
                    child = self._build_layout(item_id, depth - 1 if depth > 0 else -1)
                    children.append(Variant("(ia{sv}av)", child))
            root_props = {
                "children-display": Variant("s", "submenu"),
            }
            return [0, root_props, children]
        else:
            props = self._get_item_props(parent_id)
            return [parent_id, props, []]

    def _get_item_props(self, item_id: int) -> dict:
        """Get properties for a menu item."""
        items = self._service._menu_items
        if item_id not in items:
            return {}

        label, _, enabled = items[item_id]

        if label == "separator":
            return {"type": Variant("s", "separator")}

        return {
            "label": Variant("s", label),
            "enabled": Variant("b", enabled),
            "visible": Variant("b", True),
        }

    def notify_layout_update(self):
        """Increment revision and signal update."""
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
        self._bus_name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"

        self._sni_interface = StatusNotifierItemInterface(self)
        self._menu_interface = DBusMenuInterface(self)

        # Menu items: id -> (label, callback, enabled)
        self._menu_items = {
            1: ("Start Gamescope", self._do_start, True),
            2: ("Stop Gamescope", self._do_stop, False),
            3: ("separator", None, True),
            4: ("Quit", self._do_quit, True),
        }

    async def connect(self):
        """Connect to D-Bus and register interfaces."""
        self._bus = await MessageBus(bus_type=BusType.SESSION).connect()

        # Export interfaces
        self._bus.export("/StatusNotifierItem", self._sni_interface)
        self._bus.export("/MenuBar", self._menu_interface)

        # Request bus name
        await self._bus.request_name(self._bus_name)

        print(f"D-Bus name: {self._bus_name}")

        # Register with StatusNotifierWatcher
        try:
            introspection = await self._bus.introspect(
                self.WATCHER_BUS, self.WATCHER_PATH
            )
            proxy = self._bus.get_proxy_object(
                self.WATCHER_BUS, self.WATCHER_PATH, introspection
            )
            watcher = proxy.get_interface("org.kde.StatusNotifierWatcher")
            await watcher.call_register_status_notifier_item(self._bus_name)
            print("Registered with StatusNotifierWatcher")
        except Exception as e:
            print(f"Warning: Could not register with StatusNotifierWatcher: {e}")
            print("Is a StatusNotifier host (waybar, KDE, etc.) running?")

    async def disconnect(self):
        """Disconnect from D-Bus."""
        if self._bus:
            self._bus.disconnect()
            self._bus = None

    async def set_status(self, status: str):
        """Set tray icon status."""
        is_running = status == "Active"

        # Update menu items
        self._menu_items[1] = ("Start Gamescope", self._do_start, not is_running)
        self._menu_items[2] = ("Stop Gamescope", self._do_stop, is_running)

        # Update status and emit signals
        self._sni_interface.update_status(status)
        self._menu_interface.notify_layout_update()

    def _handle_click(self, item_id: int):
        """Handle menu item click."""
        print(f"Menu click: item {item_id}")
        if item_id in self._menu_items:
            label, callback, enabled = self._menu_items[item_id]
            print(f"  -> {label}, enabled={enabled}")
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
