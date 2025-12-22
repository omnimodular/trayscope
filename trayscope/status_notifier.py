"""StatusNotifier D-Bus implementation for system tray support."""

import os
from gi.repository import Gio, GLib

# StatusNotifierItem D-Bus interface
SNI_INTERFACE = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
  </interface>
</node>
"""

# DBusMenu interface for the menu
DBUSMENU_INTERFACE = """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps" type="a(ia{sv})"/>
      <arg name="removedProps" type="a(ias)"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent" type="i"/>
    </signal>
  </interface>
</node>
"""


class StatusNotifierItem:
    """StatusNotifier D-Bus service for system tray integration."""

    WATCHER_BUS_NAME = "org.kde.StatusNotifierWatcher"
    WATCHER_PATH = "/StatusNotifierWatcher"
    WATCHER_INTERFACE = "org.kde.StatusNotifierWatcher"

    def __init__(self, on_start=None, on_stop=None, on_settings=None,
                 on_logs=None, on_quit=None):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_settings = on_settings
        self.on_logs = on_logs
        self.on_quit = on_quit

        self._status = "Passive"  # Passive, Active, NeedsAttention
        self._bus = None
        self._sni_registration_id = None
        self._menu_registration_id = None
        self._watcher_subscription = None
        self._menu_revision = 1

        # Menu items: id -> (label, callback, enabled)
        self._menu_items = {
            1: ("Start Gamescope", self._do_start, True),
            2: ("Stop Gamescope", self._do_stop, False),
            3: ("separator", None, True),
            4: ("Settings...", self._do_settings, True),
            5: ("View Logs...", self._do_logs, True),
            6: ("separator", None, True),
            7: ("Quit", self._do_quit, True),
        }

    @property
    def bus_name(self):
        """Get our bus name."""
        return f"org.kde.StatusNotifierItem-{os.getpid()}-1"

    @property
    def object_path(self):
        """Get our object path."""
        return "/StatusNotifierItem"

    @property
    def menu_path(self):
        """Get menu object path."""
        return "/MenuBar"

    def register(self):
        """Register with the StatusNotifierWatcher."""
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        # Register StatusNotifierItem interface
        node_info = Gio.DBusNodeInfo.new_for_xml(SNI_INTERFACE)
        self._sni_registration_id = self._bus.register_object(
            self.object_path,
            node_info.interfaces[0],
            self._handle_sni_method_call,
            self._handle_sni_get_property,
            None
        )

        # Register DBusMenu interface
        menu_node_info = Gio.DBusNodeInfo.new_for_xml(DBUSMENU_INTERFACE)
        self._menu_registration_id = self._bus.register_object(
            self.menu_path,
            menu_node_info.interfaces[0],
            self._handle_menu_method_call,
            self._handle_menu_get_property,
            None
        )

        # Request our bus name
        Gio.bus_own_name_on_connection(
            self._bus,
            self.bus_name,
            Gio.BusNameOwnerFlags.NONE,
            self._on_name_acquired,
            self._on_name_lost
        )

    def _on_name_acquired(self, connection, name):
        """Called when we acquire our bus name."""
        # Register with StatusNotifierWatcher
        try:
            self._bus.call_sync(
                self.WATCHER_BUS_NAME,
                self.WATCHER_PATH,
                self.WATCHER_INTERFACE,
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (self.bus_name,)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
        except GLib.Error as e:
            print(f"Failed to register with StatusNotifierWatcher: {e}")

    def _on_name_lost(self, connection, name):
        """Called when we lose our bus name."""
        print(f"Lost bus name: {name}")

    def unregister(self):
        """Unregister from D-Bus."""
        if self._sni_registration_id:
            self._bus.unregister_object(self._sni_registration_id)
        if self._menu_registration_id:
            self._bus.unregister_object(self._menu_registration_id)

    def set_status(self, status):
        """Set the status (passive, active, needs-attention)."""
        status_map = {
            'passive': 'Passive',
            'active': 'Active',
            'needs-attention': 'NeedsAttention'
        }
        new_status = status_map.get(status.lower(), 'Passive')
        if new_status != self._status:
            self._status = new_status
            # Update menu items
            is_running = new_status == 'Active'
            self._menu_items[1] = ("Start Gamescope", self._do_start, not is_running)
            self._menu_items[2] = ("Stop Gamescope", self._do_stop, is_running)
            self._emit_new_status()
            self._emit_layout_updated()

    def _emit_new_status(self):
        """Emit NewStatus signal."""
        if self._bus:
            self._bus.emit_signal(
                None,
                self.object_path,
                "org.kde.StatusNotifierItem",
                "NewStatus",
                GLib.Variant("(s)", (self._status,))
            )

    def _emit_layout_updated(self):
        """Emit LayoutUpdated signal."""
        self._menu_revision += 1
        if self._bus:
            self._bus.emit_signal(
                None,
                self.menu_path,
                "com.canonical.dbusmenu",
                "LayoutUpdated",
                GLib.Variant("(ui)", (self._menu_revision, 0))
            )

    def _handle_sni_method_call(self, connection, sender, object_path,
                                 interface_name, method_name, parameters,
                                 invocation):
        """Handle StatusNotifierItem method calls."""
        if method_name == "Activate":
            if self.on_settings:
                self.on_settings()
            invocation.return_value(None)
        elif method_name == "SecondaryActivate":
            invocation.return_value(None)
        elif method_name == "ContextMenu":
            invocation.return_value(None)
        elif method_name == "Scroll":
            invocation.return_value(None)
        else:
            invocation.return_error_literal(
                Gio.dbus_error_quark(),
                Gio.DBusError.UNKNOWN_METHOD,
                f"Unknown method: {method_name}"
            )

    def _handle_sni_get_property(self, connection, sender, object_path,
                                  interface_name, property_name):
        """Handle StatusNotifierItem property gets."""
        props = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "trayscope"),
            "Title": GLib.Variant("s", "Trayscope"),
            "Status": GLib.Variant("s", self._status),
            "IconName": GLib.Variant("s", "applications-games"),
            "IconThemePath": GLib.Variant("s", ""),
            "Menu": GLib.Variant("o", self.menu_path),
            "ItemIsMenu": GLib.Variant("b", True),
        }
        return props.get(property_name)

    def _handle_menu_method_call(self, connection, sender, object_path,
                                  interface_name, method_name, parameters,
                                  invocation):
        """Handle DBusMenu method calls."""
        if method_name == "GetLayout":
            parent_id, depth, props = parameters.unpack()
            layout = self._build_layout(parent_id, depth)
            invocation.return_value(GLib.Variant("(u(ia{sv}av))",
                                                  (self._menu_revision, layout)))
        elif method_name == "GetGroupProperties":
            ids, prop_names = parameters.unpack()
            result = []
            for item_id in ids:
                if item_id in self._menu_items:
                    props = self._get_item_properties(item_id)
                    result.append((item_id, props))
            invocation.return_value(GLib.Variant("(a(ia{sv}))", (result,)))
        elif method_name == "GetProperty":
            item_id, prop_name = parameters.unpack()
            props = self._get_item_properties(item_id)
            if prop_name in props:
                invocation.return_value(GLib.Variant("(v)", (props[prop_name],)))
            else:
                invocation.return_error_literal(
                    Gio.dbus_error_quark(),
                    Gio.DBusError.INVALID_ARGS,
                    f"Unknown property: {prop_name}"
                )
        elif method_name == "Event":
            item_id, event_id, data, timestamp = parameters.unpack()
            if event_id == "clicked" and item_id in self._menu_items:
                label, callback, enabled = self._menu_items[item_id]
                if callback and enabled:
                    GLib.idle_add(callback)
            invocation.return_value(None)
        elif method_name == "AboutToShow":
            item_id = parameters.unpack()[0]
            invocation.return_value(GLib.Variant("(b)", (False,)))
        else:
            invocation.return_error_literal(
                Gio.dbus_error_quark(),
                Gio.DBusError.UNKNOWN_METHOD,
                f"Unknown method: {method_name}"
            )

    def _handle_menu_get_property(self, connection, sender, object_path,
                                   interface_name, property_name):
        """Handle DBusMenu property gets."""
        props = {
            "Version": GLib.Variant("u", 3),
            "Status": GLib.Variant("s", "normal"),
            "TextDirection": GLib.Variant("s", "ltr"),
            "IconThemePath": GLib.Variant("as", []),
        }
        return props.get(property_name)

    def _build_layout(self, parent_id, depth):
        """Build menu layout structure."""
        if parent_id == 0:
            # Root menu
            children = []
            for item_id in sorted(self._menu_items.keys()):
                child_layout = self._build_layout(item_id, depth - 1 if depth > 0 else 0)
                children.append(GLib.Variant("v", GLib.Variant("(ia{sv}av)", child_layout)))
            return (0, {}, children)
        else:
            # Menu item
            props = self._get_item_properties(parent_id)
            return (parent_id, props, [])

    def _get_item_properties(self, item_id):
        """Get properties for a menu item."""
        if item_id not in self._menu_items:
            return {}

        label, callback, enabled = self._menu_items[item_id]

        if label == "separator":
            return {"type": GLib.Variant("s", "separator")}

        return {
            "label": GLib.Variant("s", label),
            "enabled": GLib.Variant("b", enabled),
        }

    def _do_start(self):
        if self.on_start:
            self.on_start()

    def _do_stop(self):
        if self.on_stop:
            self.on_stop()

    def _do_settings(self):
        if self.on_settings:
            self.on_settings()

    def _do_logs(self):
        if self.on_logs:
            self.on_logs()

    def _do_quit(self):
        if self.on_quit:
            self.on_quit()
