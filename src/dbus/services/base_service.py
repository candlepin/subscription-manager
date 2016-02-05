#!/usr/bin/python

import logging
import sys

log = logging.getLogger('rhsm-app.' + __name__)

# gobject and gi and python module loading tricks are fun.
gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
for gmodule in gmodules:
    del sys.modules[gmodule]


import slip._wrappers
slip._wrappers._gobject = None

from gi.repository import GLib

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service

from rhsm.dbus.services import decorators

# TODO: move these to a config/constants module
DBUS_INTERFACE = "com.redhat.Subscriptions1"
DBUS_PATH = "/com/redhat/Subscriptions1/"
PK_DEFAULT_ACTION = "com.redhat.Subscriptions1.default"


class BaseService(slip.dbus.service.Object):

    persistent = True
    _interface_name = DBUS_INTERFACE

    def __init__(self, *args, **kwargs):
        super(BaseService, self).__init__(*args, **kwargs)
        self._props = {}
        self.persistent = True

    @property
    def props(self):
        log.debug("accessing props @property")
        return self._props

    @slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    out_signature='s')
    @decorators.dbus_handle_exceptions
    def Foos(self, sender=None):
        """Just an example method that is easy to test."""
        log.debug("Foos")
        return "Foos"

    @dbus.service.signal(dbus_interface=DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("serviceStarted emit")

    def stop(self):
        """If there were shutdown tasks to do, do it here."""
        log.debug("shutting down")

    # TODO: figure out why the few codebases that use slip/python-dbus and implement
    #       Dbus.Properties do it with a staticmethod
    def _get_dbus_property(self, prop):
        log.debug("get_dbus_property, self=%s, prop=%s", self, prop)
        if prop in self._props:
            return self._props[prop]
        else:
            raise dbus.exceptions.DBusException("org.freedesktop.DBus.Error.AccessDenied: "
                                                "Property '%s' isn't exported (or may not exist)"
                                                 % prop)

    #
    # org.freedesktop.DBus.Properties interface
    #
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self._get_dbus_property(property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='s',
                                   out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        # TODO: use better test type conversion ala dbus_utils.py
        if interface_name != self._interface_name:
            raise dbus.exceptions.DBusException("%s can not getAll() properties for %s" % (self._interface_name,
                                                                                           interface_name))

        log.debug("GetAll interface_name=%s, sender=%s", interface_name, sender)

        # TODO/FIXME: error handling, etc
        return self.props

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        log.debug("Properties Changed emitted.")


def start_signal(service):
    service.ServiceStarted()
    return False


# factory?
def run_service(bus_class, dbus_interface, dbus_path, service_class):
    """bus == dbus.SystemBus() etc.
    service_class is the the class implementing a DBus Object/service."""

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    bus = bus_class()

    name = dbus.service.BusName(dbus_interface, bus)
    service = service_class(name, dbus_path)

    mainloop = GLib.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    GLib.idle_add(start_signal, service)

    try:
        mainloop.run()
    except KeyboardInterrupt, e:
        log.exception(e)
    except SystemExit, e:
        log.exception(e)
        log.debug("system exit")
    except Exception, e:
        log.exception(e)

    if service:
        service.stop()


def run():
    run_service(dbus.SystemBus(), DBUS_INTERFACE, DBUS_PATH, BaseService)
