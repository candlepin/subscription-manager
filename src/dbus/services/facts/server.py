#!/usr/bin/python

import logging
import os
import sys
print sys.path
# Entry point needs to setup sys.path so subscription_manager
# is found. Ie, add /usr/share/rhsm/ to sys.path

log = logging.getLogger('rhsm-app.' + __name__)


#from subscription_manager.ga import GObject as ga_GObject
#from subscription_manager.ga import GLib as ga_GLib


print "sys.modules['gobject']: %s" % sys.modules.get('gobject', 'No gobject found')
gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
for gmodule in gmodules:
    print "del %s" % gmodule
    del sys.modules[gmodule]

gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
import pprint
pprint.pprint(gmodules)

print "sys.modules['gobject']: %s" % sys.modules.get('gobject', 'No gobject found')

import slip._wrappers
slip._wrappers._gobject = None

from gi.repository import GLib
#sys.modules['gobject'] = GObject


import datetime

import dbus
import dbus.service
import dbus.mainloop.glib

import slip

# FIXME: hack, monkey patch slip._wrappers._gobject so it doesn't try to outsmart gobject import
#import slip._wrappers
#slip._wrappers._gobject = ga_GObject

import slip.dbus
import slip.dbus.service

from rhsm.dbus.services.facts import decorators


# TODO: move these to a config/constants module
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts"


def debug(sig, frame):
    import pdb
    pdb.set_trace()


import signal
log.debug("signal.DFL %s", signal.SIG_DFL)
log.debug("signal sigint %s", signal.getsignal(signal.SIGINT))
signal.signal(signal.SIGUSR1, debug)
signal.signal(signal.SIGINT, debug)

def dprint(*args, **kwargs):
    print args, kwargs
    log.debug(*args, **kwargs)

dprint(os.getpid())


class Facts(slip.dbus.service.Object):

    persistent = True

    def __init__(self, *args, **kwargs):
        super(Facts, self).__init__(*args, **kwargs)
        self._props = {}
        self._props['some_facts_property'] = 'some value'

    def _not_name_owner_changed(self, name, old_owner, new_owner):
        log.debug("_name_owner_changed name=%s old_owner=%s, new_owner=%s",
                  name, old_owner, new_owner)
        return super(Facts, self)._name_owner_changed(name, old_owner, new_owner)

    # use the newer version of this
    def not_sender_seen(self, sender):
        log.debug("sender_seen sender=%s", sender)
        log.debug("Facts.senders=%s", Facts.senders)
        log.debug("Facts.connections_senders=%s", Facts.connections_senders)
        log.debug("Facts.connections_smobjs=%s", Facts.connections_smobjs)
        if (sender, self.connection) not in Facts.senders:
            Facts.senders.add((sender, self.connection))
            if self.connection not in Facts.connections_senders:
                Facts.connections_senders[self.connection] = set()
                Facts.connections_smobjs[self.connection] = \
                    self.connection.add_signal_receiver(
                        handler_function=self._name_owner_changed,
                        signal_name='NameOwnerChanged',
                        dbus_interface='org.freedesktop.DBus',
                        arg1=sender)
            Facts.connections_senders[self.connection].add(sender)

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s, int_a, int_b")
        total = int_a + int_b
        return total

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        log.debug("Return42")
        return '42'

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    out_signature='i')
    def getPid(self, sender=None):
        pid = os.getpid()
        return pid

    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='b')
    @decorators.dbus_handle_exceptions
    def ProvokePropertyChange(self, sender=None):
        log.debug("ProvokePropertyChange")
        #log.debug("ProvokePropertyChange sender=%s", sender)
        timestamp = 'some value %s' % datetime.datetime.now().isoformat()
        #self._props['some_facts_property'] = timestamp
        log.debug("changed some_facts_property = %s", timestamp)

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("serviceStarted emit")

    def stop(self):
        log.debug("shutting down")

    # TODO: figure out why the few codebases that use slip/python-dbus and implement
    #       Dbus.Properties do it with a staticmethod like this.
    @staticmethod
    def get_dbus_property(x, prop):
        log.debug("get_dbus_property, x=%s, prop=%s", x, prop)
        if prop in x._props:
            return x._props[prop]
        else:
            raise dbus.exceptions.DBusException("org.freedesktop.DBus.Error.AccessDenied: "
                                                "Property '%s' isn't exported (or may not exist)"
                                                 % prop)

    # TODO: possibly move to it's own class, possibly as a mixin
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    #@decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.get_dbus_property(self, property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='s',
                                   out_signature='a{sv}')
    #@decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        log.debug("GetAll")
        return {}
        #log.debug("GetAll interface_name=%s", interface_name)
        #log.debug("GetAll sender=%s", sender)
        # TODO/FIXME: error handling, etc
        #log.debug("GetAll returning %s", self._props)
        #return self._props

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
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
    l = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    bus = dbus.SystemBus()
    #bus = dbus.SessionBus()

    name = dbus.service.BusName(FACTS_DBUS_INTERFACE, bus)
    service = Facts(name,
                    "/Subscriptions1/Facts")

    mainloop = GLib.MainLoop()
    #mainloop = ga_GObject.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    print l
    print GLib.MainLoop
    print mainloop

    #ga_GObject.idle_add(start_signal, service)

    #ga_GObject.idle_add(provoke_prop, service)

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
