#!/usr/bin/python

import logging

log = logging.getLogger(__name__)

from rhsm.dbus.common import gi_kluge
gi_kluge.kluge_it()

from gi.repository import GLib

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service

from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_properties
#from rhsm.dbus.common import dbus_utils

# TODO: move these to a config/constants module
# Name of the dbus service
DEFAULT_DBUS_BUS_NAME = "com.redhat.Subscriptions1"

# Name of the DBus interface provided by this object
# Note: This could become multiple interfaces
DEFAULT_DBUS_INTERFACE = "com.redhat.Subscriptions1"

# Where in the DBus object namespace does this object live
DEFAULT_DBUS_PATH = "/com/redhat/Subscriptions1"

# The polkit action-id to use by default if none are specified
PK_DEFAULT_ACTION = "com.redhat.Subscriptions1.default"


class BaseService(slip.dbus.service.Object):

    persistent = True
    _interface_name = DEFAULT_DBUS_INTERFACE
    default_polkit_auth_required = PK_DEFAULT_ACTION
    default_dbus_path = DEFAULT_DBUS_PATH
    default_polkit_auth_required = None

    def __init__(self, conn=None, object_path=None, bus_name=None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.log.debug("conn=%s", conn)
        self.log.debug("object_path=%s", object_path)
        self.log.debug("bus_name=%s", bus_name)
        self.log.debug("self._interface_name=%s", self._interface_name)
        self.log.debug("self.default_dbus_path=%s", self.default_dbus_path)

        super(BaseService, self).__init__(conn=conn,
                                          object_path=self.default_dbus_path,
                                          bus_name=bus_name)

        self._props = self._create_props()
        self.persistent = True

    def _create_props(self):
        properties = base_properties.BaseProperties(self._interface_name,
                                                    {'default_sample_prop':
                                                     'default_sample_value'},
                                                    self.PropertiesChanged)
        return properties

    @property
    def props(self):
        self.log.debug("accessing props @property")
        return self._props

    @dbus.service.signal(dbus_interface=DEFAULT_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        self.log.debug("serviceStarted emit")

    # FIXME: more of a 'server' than 'service', so move it when we split
    def stop(self):
        """If there were shutdown tasks to do, do it here."""
        self.log.debug("shutting down")

    #
    # org.freedesktop.DBus.Properties interface
    #
    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        self.log.debug("Properties Changed emitted.")

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='s',
                                    out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        self.log.debug("GetAll() interface_name=%s", interface_name)
        self.log.debug("sender=%s", sender)
        return self.props.get_all(interface_name=interface_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        self.log.debug("Get() interface_name=%s property_name=%s", interface_name, property_name)
        self.log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.props.get(interface_name=interface_name,
                              property_name=property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ssv')
    @decorators.dbus_handle_exceptions
    def Set(self, interface_name, property_name, new_value, sender=None):
        """Set a DBus property on this object.

        This is the base service class, and defaults to DBus properties
        being read-only. Attempts to Set a property will raise a
        DBusException of type org.freedesktop.DBus.Error.AccessDenied.

        Subclasses that need settable properties should override this."""

        log.debug("Set() interface_name=%s property_name=%s", interface_name, property_name)
        log.debug("Set() PPPPPPPPPPPPP self.props=%s %s", self.props, type(self.props))

        self.props.set(interface_name=interface_name,
                       property_name=property_name,
                       new_value=new_value)

    # Kluges

    # override the rhel7 slip version with a newer version that
    # includes upstream ea81f96a7746a4872e923b31dae646d1afa0043b
    # ie, don't listen to all NameOwnerChanged signals
    # TODO: This is likely optional on RHEL7, and should be removed
    #       especially if python-slip gets updated for RHEL7.
    def sender_seen(self, sender):
        if (sender, self.connection) not in BaseService.senders:
            BaseService.senders.add((sender, self.connection))
            if self.connection not in BaseService.connections_senders:
                BaseService.connections_senders[self.connection] = set()
                BaseService.connections_smobjs[self.connection] = \
                    self.connection.add_signal_receiver(
                        handler_function=self._name_owner_changed,
                        signal_name='NameOwnerChanged',
                        dbus_interface='org.freedesktop.DBus',
                        arg1=sender)
            BaseService.connections_senders[self.connection].add(sender)


def start_signal(service):
    service.ServiceStarted()
    return False


service_classes = []


# factory?
def run_services(bus_class=None):
    """bus == dbus.SystemBus() etc.
    service_class is the the class implementing a DBus Object/service."""

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    bus_class = bus_class or dbus.SystemBus
    bus = bus_class()

    BUS_NAME = "com.redhat.Subscriptions1.Facts"
    log.debug("service_classes=%s", service_classes)
    for service_class in service_classes:
        name = dbus.service.BusName(BUS_NAME, bus)
        log.debug("service_class=%s", service_class)
        log.debug("service_class.default_dbus_path=%s", service_class.default_dbus_path)
        service = service_class(name,
                                service_class.default_dbus_path)

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
    run_services()
    #run_service(dbus.SystemBus(), DBUS_BUS_NAME, DBUS_INTERFACE, DBUS_PATH, BaseService)
