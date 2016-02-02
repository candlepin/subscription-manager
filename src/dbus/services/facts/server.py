#!/usr/bin/python

import logging

import sys
print sys.path
# Entry point needs to setup sys.path so subscription_manager
# is found. Ie, add /usr/share/rhsm/ to sys.path

log = logging.getLogger('rhsm-app.' + __name__)


from subscription_manager.ga import GObject as ga_GObject
#from subscription_manager.ga import GLib as ga_GLib

import datetime

import dbus
import dbus.service
import dbus.mainloop.glib

import slip

# FIXME: hack, monkey patch slip._wrappers._gobject so it doesn't try to outsmart gobject import
import slip._wrappers
slip._wrappers._gobject = ga_GObject

import slip.dbus
import slip.dbus.service

from rhsm.dbus.services.facts import decorators


FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts"


class Facts(slip.dbus.service.Object):
    _props = {}

    def __init__(self, *args, **kwargs):
        super(Facts, self).__init__(*args, **kwargs)
        self._props['some_facts_property'] = 'some value'

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        total = int_a + int_b
        return total

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='i')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        return 42

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='b')
    @decorators.dbus_handle_exceptions
    def ProvokePropertyChange(self, sender=None):
        self._props['some_facts_property'] = 'some value %s' % datetime.datetime.now().isoformat()

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE)
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("serviceStarted emit")

    def stop(self):
        log.debug("shutting down")

    @staticmethod
    def get_dbus_property(x, prop):
        if prop in x._props:
            return x._props[prop]
        else:
            raise dbus.exceptions.DBusException("org.freedesktop.DBus.Error.AccessDenied: "
                                                "Property '%s' isn't exported (or may not exist)"
                                                 % prop)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.get_dbus_property(self, property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='s',
                                   out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        # TODO/FIXME: error handling, etc
        return self._props

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    @decorators.dbus_handle_exceptions
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        log.debug("Facts service Properties Changed emitted.")


def start_signal(service):
    service.ServiceStarted()
    return False


def provoke_prop(service):
    service.ProvokePropertyChange()
    return False


def run():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    #bus = dbus.SessionBus()

    name = dbus.service.BusName(FACTS_DBUS_INTERFACE, bus)
    service = Facts(name, "/com/redhat/Subscriptions1/Facts")

    mainloop = ga_GObject.MainLoop()
#    slip.dbus.service.set_mainloop(mainloop)

    ga_GObject.idle_add(start_signal, service)

    ga_GObject.idle_add(provoke_prop, service)
    try:
        mainloop.run()
    except KeyboardInterrupt, e:
        log.exception(e)
    except Exception, e:
        log.exception(e)
    except SystemExit, e:
        log.exception(e)
        log.debug("system exit")

    if service:
        service.stop()
