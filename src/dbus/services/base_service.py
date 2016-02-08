#!/usr/bin/python

import logging
import sys

log = logging.getLogger(__name__)

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
from rhsm.dbus.services import base_properties

# TODO: move these to a config/constants module
# Name of the dbus service
DBUS_BUS_NAME = "com.redhat.Subscriptions1"
# Name of the DBus interface provided by this object
# Note: This could become multiple interfaces
DBUS_INTERFACE = "com.redhat.Subscriptions1"
# Where in the DBus object namespace does this object live
DBUS_PATH = "/com/redhat/Subscriptions1/"
# The polkit action-id to use by default if none are specified
PK_DEFAULT_ACTION = "com.redhat.Subscriptions1.default"


class BaseService(slip.dbus.service.Object):

    persistent = True
    _interface_name = DBUS_INTERFACE
    default_polkit_auth_required = PK_DEFAULT_ACTION

    def __init__(self, *args, **kwargs):
        super(BaseService, self).__init__(*args, **kwargs)
        self._props = base_properties.BaseProperties(self._interface_name,
                                                    {'default_sample_prop':
                                                     'default_sample_value'},
                                                    self.PropertiesChanged)
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

    #
    # org.freedesktop.DBus.Properties interface
    #
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.props.get(interface=interface_name,
                              prop=property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='s',
                                   out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        # TODO: use better test type conversion ala dbus_utils.py
        log.debug("GetAll interface_name=%s, sender=%s", interface_name, sender)

        return self.props.get_all(interface=interface_name)

    # TODO: pk action for changing properties
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ssv')
    @decorators.dbus_handle_exceptions
    def Set(self, interface_name, property_name, new_value, sender=None):
        self.props.set(interface=interface_name,
                       prop=property_name,
                       value=new_value)

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        log.debug("Properties Changed emitted.")


def start_signal(service):
    service.ServiceStarted()
    return False


# factory?
def run_service(bus_class, bus_name, dbus_interface, dbus_path, service_class):
    """bus == dbus.SystemBus() etc.
    service_class is the the class implementing a DBus Object/service."""

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    bus = bus_class()

    name = dbus.service.BusName(bus_name, bus)
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
    run_service(dbus.SystemBus(), DBUS_BUS_NAME, DBUS_INTERFACE, DBUS_PATH, BaseService)
