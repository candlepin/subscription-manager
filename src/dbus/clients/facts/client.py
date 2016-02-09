#
# Client DBus proxy for rhsm facts service
#
# Copyright (c) 2010-2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import logging
import sys

# FIXME: Remove, just needed for testing
sys.path.append("/usr/share/rhsm")
from subscription_manager import logutil
logutil.init_logger()

import dbus
import dbus.mainloop.glib

from rhsm.dbus.common import gi_kluge
gi_kluge.kluge_it()

# FIXME: GLib imported to start it's main loop,
#        but this is a library-ish module, that should
#        be up to the 'app'
from gi.repository import GLib

import slip.dbus
import slip.dbus.polkit

#from slip.dbus import polkit

from rhsm.dbus.common import decorators


log = logging.getLogger('rhsm.dbus.clients.facts.client')

# TODO: share
FACTS_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.User"
#FACTS_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.Root"
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/User"
#FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/Root"


class FactsProxy(object):
    default_bus_class = dbus.SystemBus
    default_bus_name = FACTS_DBUS_BUS_NAME
    default_interface = FACTS_DBUS_INTERFACE
    default_path = FACTS_DBUS_PATH

    def __init__(self,
                 dbus_bus_class=None,
                 dbus_bus_name=None,
                 dbus_interface=None,
                 dbus_path=None):
        self.bus_class = dbus_bus_class or self.default_bus_class
        self.bus_name = dbus_bus_name or self.default_bus_name
        self.interface = dbus_interface or self.default_interface
        self.path = dbus_path or self.default_path

        self.bus = self.bus_class()
        self.dbus_object = self.bus.get_object(self.bus_name,
                                               self.path)
        self.facts = dbus.Interface(self.dbus_object,
                                    dbus_interface=self.interface)
        self.facts_props = dbus.Interface(self.dbus_object,
                                          dbus_interface=dbus.PROPERTIES_IFACE)

        self.dbus_bus_object = self.bus.get_object(dbus.BUS_DAEMON_NAME,
                                                  dbus.BUS_DAEMON_PATH)
        self.dbus_intf = dbus.Interface(self.dbus_bus_object,
                                        dbus_interface=dbus.BUS_DAEMON_IFACE)

        self.facts.connect_to_signal("ServiceStarted", self._on_service_started,
                                     sender_keyword='sender', destination_keyword='destination',
                                     interface_keyword='interface', member_keyword='member',
                                     path_keyword='path')
        self.facts_props.connect_to_signal("PropertiesChanged", self._on_properties_changed,
                                           sender_keyword='sender', destination_keyword='destination',
                                           interface_keyword='interface', member_keyword='member',
                                           path_keyword='path')
        self.dbus_intf.connect_to_signal("NameOwnerChanged", self._on_name_owner_changed,
                                         sender_keyword='sender', destination_keyword='destination',
                                         interface_keyword='interface', member_keyword='member',
                                         path_keyword='path')

        self.bus.call_on_disconnection(self._on_bus_disconnect)

    @decorators.dbus_handle_exceptions
    @slip.dbus.polkit.enable_proxy
    def Return42(self):
        log.debug("Return42 pre")
        ret = self.facts.Return41()
        log.debug("Return42 post, ret=%s", ret)
        return ret

    def signal_handler(self, *args, **kwargs):
        print "signal_handler"
        print args
        print kwargs
        log.debug("signal_handler args=%s kwargs=%s", args, kwargs)

    def _on_service_started(self, *args, **kwargs):
        self.signal_handler(*args, **kwargs)

    def _on_properties_changed(self, *args, **kwargs):
        self.signal_handler(*args, **kwargs)

    def _on_name_owner_changed(self, *args, **kwargs):
        self.signal_handler(*args, **kwargs)

    def _on_bus_disconnect(self, connection):
        self.dbus_bus_object = None
        log.debug("disconnected")


def call_42(fact_proxy):
    ret = fact_proxy.Return42()
    log.debug("call_42 ret=%s", ret)
    return False


def get_props(props_proxy, intf):
    ret = props_proxy.GetAll(intf)
    log.debug("get_props ret=%s", str(ret))
    return False


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    #dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    facts_proxy = FactsProxy()
#    ret = facts_proxy.facts.Return42()
#    log.debug("return42=%s", ret)
#    print ret

#    ret = facts_proxy.facts_props.GetAll('com.redhat.Subscriptions1.Facts')
#    log.debug("GetAll=%s", dir(ret))
#    print ret

    GLib.idle_add(call_42, facts_proxy.facts)
    GLib.idle_add(get_props,
                  facts_proxy.facts_props, 'com.redhat.Subscriptions1.Facts')

    try:
        mainloop.run()
    except KeyboardInterrupt, e:
        log.exception(e)
    except SystemExit, e:
        log.exception(e)
        log.debug("system exit")
    except Exception, e:
        log.exception(e)

if __name__ == "__main__":
    sys.exit(main())
