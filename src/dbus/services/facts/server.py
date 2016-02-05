#!/usr/bin/python

import logging
import os
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

from rhsm.dbus.services.facts import decorators

# TODO: move these to a config/constants module
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.collect"


class Facts(slip.dbus.service.Object):

    persistent = True

    def __init__(self, *args, **kwargs):
        super(Facts, self).__init__(*args, **kwargs)
        self._props = {'some_default_prop': 'the_default_props_value'}
        self.persistent = True

    @property
    def props(self):
        log.debug("accessing props @property")
        return self._props

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s, int_a, int_b")
        total = int_a + int_b
        return total

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        log.debug("Return42")
        return '42'

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    out_signature='i')
    def getPid(self, sender=None):
        pid = os.getpid()
        return pid

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("serviceStarted emit")

    def stop(self):
        log.debug("shutting down")

    # TODO: figure out why the few codebases that use slip/python-dbus and implement
    #       Dbus.Properties do it with a staticmethod like this.
    def get_dbus_property(self, prop):
        log.debug("get_dbus_property, self=%s, prop=%s", self, prop)
        if prop in self._props:
            return self._props[prop]
        else:
            raise dbus.exceptions.DBusException("org.freedesktop.DBus.Error.AccessDenied: "
                                                "Property '%s' isn't exported (or may not exist)"
                                                 % prop)

    # TODO: possibly move to it's own class, possibly as a mixin
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.get_dbus_property(property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='s',
                                   out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        if interface_name != 'com.redhat.Subscriptions1.Facts':
            raise dbus.exceptions.DBusException("Cant getAll properties for %s" % interface_name)

        log.debug("GetAll interface_name=%s, sender=%s", interface_name, sender)

        # TODO/FIXME: error handling, etc
        return self.props

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        log.debug("Facts service Properties Changed emitted.")


def start_signal(service):
    service.ServiceStarted()
    return False


def start_signal_timer(service):
    start_signal(service)
    return True


def run():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    bus = dbus.SystemBus()

    name = dbus.service.BusName(FACTS_DBUS_INTERFACE, bus)
    service = Facts(name, FACTS_DBUS_PATH)

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
