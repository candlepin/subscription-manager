#!/usr/bin/python

import logging
#import sys

log = logging.getLogger(__name__)

from rhsm.dbus.common import gi_kluge
gi_kluge.kluge_it()

# gobject and gi and python module loading tricks are fun.
#gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
#for gmodule in gmodules:
#    del sys.modules[gmodule]


#import slip._wrappers
#slip._wrappers._gobject = None

from gi.repository import GLib

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service

from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_properties

# TODO: move these to a config/constants module
# Name of the dbus service
FACTS_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts"
# Name of the DBus interface provided by this object
# Note: This could become multiple interfaces
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
# Where in the DBus object namespace does this object live
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts"
# The polkit action-id to use by default if none are specified
PK_DEFAULT_ACTION = "com.redhat.Subscriptions1.Facts.default"


class BaseService(slip.dbus.service.Object):

    persistent = True
    _interface_name = FACTS_DBUS_INTERFACE
    #default_polkit_auth_required = PK_DEFAULT_ACTION
    default_dbus_path = FACTS_DBUS_PATH
    default_polkit_auth_required = None

    def __init__(self, conn=None, object_path=None, bus_name=None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        #self.log.debug("args=%s", args)
        #self.log.debug("kwargs=%s", kwargs)
        self.log.debug("conn=%s", conn)
        self.log.debug("object_path=%s", object_path)
        self.log.debug("bus_name=%s", bus_name)
        self.log.debug("self._interface_name=%s", self._interface_name)
        self.log.debug("self.default_dbus_path=%s", self.default_dbus_path)

        super(BaseService, self).__init__(conn=conn,
                                          object_path=self.default_dbus_path,
                                          bus_name=bus_name)

        self._props = base_properties.BaseProperties(self._interface_name,
                                                    {'default_sample_prop':
                                                     'default_sample_value'},
                                                    self.PropertiesChanged)
        self.persistent = True

    # override the rhel7 slip version with a newer version that
    # includes upstream ea81f96a7746a4872e923b31dae646d1afa0043b
    # ie, don't listen to all NameOwnerChanged signals
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

    @property
    def props(self):
        self.log.debug("accessing props @property")
        return self._props

    @slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    out_signature='s')
    @decorators.dbus_handle_exceptions
    def Foos(self, sender=None):
        """Just an example method that is easy to test."""
        self.log.debug("Foos")
        return "Foos"

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        self.log.debug("serviceStarted emit")

    def stop(self):
        """If there were shutdown tasks to do, do it here."""
        self.log.debug("shutting down")

    #
    # org.freedesktop.DBus.Properties interface
    #
#    @slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
#    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
#                                    in_signature='ss',
#                                    out_signature='v')
#    #@decorators.dbus_handle_exceptions
#    def Get(self, interface_name, property_name, sender=None):
#        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
#        return self.props.get(interface=interface_name,
#                              prop=property_name)

#    @slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
#    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='s',
#                                   out_signature='a{sv}')
    #@decorators.dbus_handle_exceptions
#    def GetAll(self, interface_name, sender=None):
#        # TODO: use better test type conversion ala dbus_utils.py
#        log.debug("GetAll interface_name=%s, sender=%s", interface_name, sender)

#        return self.props.get_all(interface=interface_name)

    # TODO: pk action for changing properties
#    @slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
#    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
#                                    in_signature='ssv')
    #@decorators.dbus_handle_exceptions
#    def Set(self, interface_name, property_name, new_value, sender=None):
#        self.props.set(interface=interface_name,
#                       prop=property_name,
#                       value=new_value)
#        self.PropertiesChanged(interface_name,
#                               {property_name: new_value},
#                               [])

#    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        self.log.debug("Properties Changed emitted.")


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
