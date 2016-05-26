#!/usr/bin/python
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

import dbus

from rhsmlib.dbus import gi_kluge
gi_kluge.kluge_it()

import slip.dbus.polkit

# TODO: This is very glib2/dbus-python based. That is likely a requirement
#       for the services, but it may be worthwhile to use something more
#       modern for the client (ie, GIO based dbus support).

# TODO: maybe common.constants should just import all the constants

# FIXME: This makes client code depend on the services code being installed
#        (which it will be, but...)
from rhsmlib.dbus.services.facts import constants as facts_constants

log = logging.getLogger(__name__)


class FactsClientAuthenticationError(Exception):
    def __init__(self, *args, **kwargs):
        action_id = kwargs.pop("action_id")
        super(FactsClientAuthenticationError, self).__init__(*args, **kwargs)
        log.debug("FactsClientAuthenticationError created for %s", action_id)
        self.action_id = action_id


class FactsClient(object):
    bus_name = facts_constants.FACTS_BUS_NAME
    object_path = facts_constants.FACTS_ROOT_DBUS_PATH
    interface_name = facts_constants.FACTS_DBUS_INTERFACE

    def __init__(self, bus=None, bus_name=None, object_path=None, interface_name=None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # use default mainloop for dbus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dbus.mainloop.glib.threads_init()

        self.bus = bus or dbus.SystemBus()

        if bus_name:
            self.bus_name = bus_name

        if object_path:
            self.object_path = object_path

        if interface_name:
            self.interface_name = interface_name

        self.dbus_proxy_object = slip.dbus.proxies.ProxyObject(conn=self.bus,
                                                               bus_name=self.bus_name,
                                                               object_path=self.object_path,
                                                               follow_name_owner_changes=True)

        self.interface = dbus.Interface(self.dbus_proxy_object,
                                        dbus_interface=self.interface_name)

        self.props_interface = dbus.Interface(self.dbus_proxy_object,
                                             dbus_interface=dbus.PROPERTIES_IFACE)

        self.interface.connect_to_signal("PropertiesChanged", self._on_properties_changed,
                                         dbus_interface=dbus.PROPERTIES_IFACE,
                                         sender_keyword='sender', destination_keyword='destination',
                                         interface_keyword='interface', member_keyword='member',
                                         path_keyword='path')

        self.bus.call_on_disconnection(self._on_bus_disconnect)
        self.interface.connect_to_signal("ServiceStarted", self._on_service_started,
                                         sender_keyword='sender', destination_keyword='destination',
                                         interface_keyword='interface', member_keyword='member',
                                         path_keyword='path')

    @slip.dbus.polkit.enable_proxy(authfail_exception=FactsClientAuthenticationError)
    def GetFacts(self, *args, **kwargs):
        self.log.debug("GetFacts pre")
        ret = self.interface.GetFacts(*args, **kwargs)
        return ret

    @slip.dbus.polkit.enable_proxy(authfail_exception=FactsClientAuthenticationError)
    def GetAll(self, *args, **kwargs):
        self.log.debug("GetAll")
        ret = self.props_interface.GetAll(facts_constants.FACTS_DBUS_INTERFACE,
                                          *args, **kwargs)
        self.log.debug("GetAll res=%s", ret)
        return ret

    @slip.dbus.polkit.enable_proxy(authfail_exception=FactsClientAuthenticationError)
    def Get(self, property_name):
        self.log.debug("Get %s", property_name)
        ret = self.props_interface.Get(facts_constants.FACTS_DBUS_INTERFACE,
                                       property_name=property_name)
        return ret

    def signal_handler(self, *args, **kwargs):
        self.log.debug("signal_handler args=%s kwargs=%s", args, kwargs)

    def _on_properties_changed(self, *args, **kwargs):
        self.log.debug("PropertiesChanged")
        self.signal_handler(*args, **kwargs)

    def _on_name_owner_changed(self, *args, **kwargs):
        self.log.debug("NameOwnerChanged")
        self.signal_handler(*args, **kwargs)

    def _on_bus_disconnect(self, connection):
        self.dbus_proxy_object = None
        self.log.debug("disconnected")

    def _on_service_started(self, *args, **kwargs):
        self.log.debug("ServiceStarted")
        self.signal_handler(*args, **kwargs)


class FactsHostClient(FactsClient):
    object_path = facts_constants.FACTS_HOST_DBUS_PATH


def main():
    import dbus.mainloop.glib
    from gi.repository import GLib

    # FIXME: Remove, just needed for testing
    sys.path.append("/usr/share/rhsm")
    from subscription_manager import logutil
    logutil.init_logger()

    # ick, but otherwise logger name is __main__
    global log
    log = logging.getLogger('rhsm.dbus.clients.facts.client')

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    #slip.dbus.service.set_mainloop(mainloop)

    facts_client = FactsClient()
    facts_host_client = FactsHostClient()

    # Test passing in the object path
#    facts_read_write_client = FactsClient(object_path=facts_constants.FACTS_READ_WRITE_DBUS_PATH)

    def get_facts():
        facts_host_client.GetFacts()
        facts_client.GetFacts()
#        facts_read_write_client.GetFacts()
        return False

    def get_all_properties():
        facts_client.GetAll()
#        facts_read_write_client.GetAll()

    GLib.idle_add(get_facts)
    GLib.idle_add(get_all_properties)

    GLib.timeout_add_seconds(9, facts_client.GetFacts)
    GLib.timeout_add_seconds(11, facts_host_client.GetFacts)
#    GLib.timeout_add_seconds(13, facts_read_write_client.GetAll)

    try:
        mainloop.run()
    except KeyboardInterrupt as e:
        log.exception(e)
    except SystemExit as e:
        log.exception(e)
        log.debug("system exit")
    except Exception as e:
        log.exception(e)

    mainloop.quit()

if __name__ == "__main__":
    sys.exit(main())
