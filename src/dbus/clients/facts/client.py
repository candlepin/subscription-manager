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

#import slip.dbus
import slip.dbus.polkit

#from slip.dbus import polkit

from rhsm.dbus.common import decorators


log = logging.getLogger('rhsm.dbus.clients.facts.client')

# TODO: share
#FACTS_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.User"
FACTS_ROOT_BUS_NAME = "com.redhat.Subscriptions1.Facts.Root"
FACTS_USER_BUS_NAME = "com.redhat.Subscriptions1.Facts.User"
FACTS_INTERFACE_NAME = "com.redhat.Subscriptions1.Facts"
#FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/User"
FACTS_ROOT_OBJECT_PATH = "/com/redhat/Subscriptions1/Facts/Root"
FACTS_USER_OBJECT_PATH = "/com/redhat/Subscriptions1/Facts/User"


def error_handler(action_id=None):
    print "Authorization problem:", action_id
    log.debug("auth fail %s", action_id)


class MyAuthError(Exception):
    def __init__(self, *args, **kwargs):
        action_id = kwargs.pop("action_id")
        super(MyAuthError, self).__init__(*args, **kwargs)
        self.action_id = action_id


class FactsClient(object):
    bus_name = FACTS_ROOT_BUS_NAME
    object_path = FACTS_ROOT_OBJECT_PATH
    interface_name = FACTS_INTERFACE_NAME

    def __init__(self):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.bus = dbus.SystemBus()
        self.dbus_proxy_object = slip.dbus.proxies.ProxyObject(conn=self.bus,
                                                               bus_name=self.bus_name,
                                                               object_path=self.object_path,
                                                               follow_name_owner_changes=True)
        self.interface = dbus.Interface(self.dbus_proxy_object,
                                        dbus_interface=self.interface_name)

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

    #@slip.dbus.polkit.enable_proxy(authfail_result=False,
    #                               authfail_callback=error_handler)

#    @decorators.dbus_handle_exceptions
    @slip.dbus.polkit.enable_proxy(authfail_exception=MyAuthError)
    def Return42(self):
        self.log.debug("Return42 pre")
        ret = self.interface.Return42(timeout=5)
        self.log.debug("Return42 post, ret=%s", ret)
        print '42'
        return ret

#    @decorators.dbus_handle_exceptions
    @slip.dbus.polkit.enable_proxy(authfail_exception=MyAuthError)
    def GetFacts(self):
        self.log.debug("GetFacts pre")
        ret = self.interface.GetFacts(timeout=5)
#       self.log.debug("GetFacts post, ret=%s", ret)
        print ret
        return ret

    def signal_handler(self, *args, **kwargs):
        print "signal_handler"
        print args
        print kwargs
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


class FactsRootClient(FactsClient):
    #    @decorators.dbus_handle_exceptions
    @slip.dbus.polkit.enable_proxy(authfail_exception=MyAuthError)
    def Return42(self):
        self.log.debug("Return42 pre")
        ret = self.interface.Return42(timeout=5)
        self.log.debug("Return42 post, ret=%s", ret)
        print '42'
        return ret

#    @decorators.dbus_handle_exceptions
    @slip.dbus.polkit.enable_proxy(authfail_exception=MyAuthError)
    def GetFacts(self):
        self.log.debug("GetFacts pre")
        ret = self.interface.GetFacts(timeout=5)
#       self.log.debug("GetFacts post, ret=%s", ret)
        print ret
        return ret


class FactsUserClient(FactsClient):
    bus_name = FACTS_USER_BUS_NAME
    object_path = FACTS_USER_OBJECT_PATH
    interface_name = FACTS_INTERFACE_NAME


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    #slip.dbus.service.set_mainloop(mainloop)

    facts_root_client = FactsRootClient()
    facts_user_client = FactsUserClient()

#    ret = facts_proxy.facts_props.GetAll('com.redhat.Subscriptions1.Facts')
#    log.debug("GetAll=%s", dir(ret))
#    print ret
    def get_facts():
        facts_user_client.GetFacts()
        facts_root_client.GetFacts()
        return False

    GLib.idle_add(get_facts)
    GLib.timeout_add_seconds(5, facts_root_client.Return42)
    GLib.timeout_add_seconds(15, facts_root_client.GetFacts)
    GLib.timeout_add_seconds(5, facts_user_client.Return42)
    GLib.timeout_add_seconds(15, facts_user_client.GetFacts)
    #GLib.idle_add(call_42, facts_proxy.facts)
    #GLib.idle_add(get_props,
    #              facts_proxy.facts_props,
    #              'com.redhat.Subscriptions1.Facts')
    try:
        mainloop.run()
    except KeyboardInterrupt, e:
        log.exception(e)
    except SystemExit, e:
        log.exception(e)
        log.debug("system exit")
    except Exception, e:
        log.exception(e)

    mainloop.quit()

if __name__ == "__main__":
    sys.exit(main())
