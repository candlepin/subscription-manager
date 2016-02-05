#!/usr/bin/python

import logging
import os
import sys
#print sys.path
# Entry point needs to setup sys.path so subscription_manager
# is found. Ie, add /usr/share/rhsm/ to sys.path

log = logging.getLogger('rhsm-app.' + __name__)


#from subscription_manager.ga import GObject as ga_GObject
#from subscription_manager.ga import GLib as ga_GLib

#import pprint
#pprint.pprint(sys.modules)

#print "sys.modules['gobject']: %s" % sys.modules.get('gobject', 'No gobject found')
gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
for gmodule in gmodules:
    del sys.modules[gmodule]

gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
#pprint.pprint(gmodules)

#print "sys.modules['gobject']: %s" % sys.modules.get('gobject', 'No gobject found')

import slip._wrappers
slip._wrappers._gobject = None

from gi.repository import GLib
#sys.modules['gobject'] = GObject


import datetime

import dbus
import dbus.service
import dbus.mainloop.glib

#import slip

# FIXME: hack, monkey patch slip._wrappers._gobject so it doesn't try to outsmart gobject import
#import slip._wrappers
#slip._wrappers._gobject = ga_GObject

import slip.dbus
import slip.dbus.service

from rhsm.dbus.services.facts import decorators


# TODO: move these to a config/constants module
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.collect"


class OrgFreedesktopDBusInterfaceMixin(object):
    pass


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
    #@staticmethod
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
        log.debug("GetAll returning %s", self.props)
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
    #bus = dbus.SessionBus()

    name = dbus.service.BusName(FACTS_DBUS_INTERFACE, bus)
    service = Facts(name, FACTS_DBUS_PATH)

    mainloop = GLib.MainLoop()
    #mainloop = ga_GObject.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    GLib.idle_add(start_signal, service)

    GLib.timeout_add_seconds(7, start_signal_timer, service)

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
