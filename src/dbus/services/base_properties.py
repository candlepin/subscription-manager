import logging

import dbus

log = logging.getLogger(__name__)


# TODO: Make properties class a gobject, so we can reused it's prop handling
#       (And maybe python-dbus can do something useful with a Gobject?
class BaseProperties(object):
    def __init__(self, interface,
                 data=None,
                 prop_changed_callback=None):
        self.data = data
        self.interface = interface
        self.prop_changed_callback = prop_changed_callback

    def get(self, interface=None, prop=None):
        self._check_interface(interface)
        self._check_prop(prop)

        try:
            return self.data[prop]
        except KeyError, e:
            log.exception(e)
            msg = "org.freedesktop.DBus.Error.AccessDenied: "
            "Property '%s' isn't exported (or may not exist) on interface: %s" % (prop, self.interface)

            raise dbus.exceptions.DBusException(msg)

    def get_all(self, interface=None):
        self._check_interface(interface)

        # For now at least, likely need to filter
        return self.data

    def set(self, interface, prop, value):
        self._check_interface(interface)
        self._check_prop(prop)

        # FIXME/TODO: Plug in access checks and data validation
        try:
            prop = str(prop)
            self.data[prop] = value
        except Exception, e:
            self._set_error(e, prop, value)

    def _check_interface(self, interface):
        if interface and interface != self.interface:
            msg = "org.freedesktop.DBus.Error.UnknownInterface: "
            "%s does not handle properties for %s" % (self.interface, interface)
            raise dbus.exceptions.DBusException(msg)
        # Unset None/'' interface is default

    def _check_prop(self, prop):
        if prop not in self.data:
            msg = "org.freedesktop.DBus.Error.AccessDenied: "
            "Property '%s' does not exist" % property
            raise dbus.exceptions.DBusException(msg)

    def _set_error(self, exception, prop, value):
        log.exception(exception)
        msg = "Error setting property %s=%s on interface=%s: %s" % (prop,
                                                                    value,
                                                                    self.interface,
                                                                    exception)
        raise dbus.exceptions.DBusException(msg)
