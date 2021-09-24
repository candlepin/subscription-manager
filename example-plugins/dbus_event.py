# Copyright (c) 2013 Red Hat, Inc.
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
import dbus
import dbus.service
import dbus.glib

from subscription_manager.base_plugin import SubManPlugin
requires_api_version = "1.0"

# This connects to the dbus system bus and emits dbus
# signals for each hook we run. At the moment, the signals
# are just strings that match the hook name.
#
# To see the events being emitted, you can run:
#
#   dbus-monitor --system
#
# or to just monitor the subman plugin event signals:
#
#         dbus-monitor --system "type='signal', interface='com.redhat.SubscriptionManager.PluginEvent'"
#


# FIXME: this dbus stuff is almost surely not complete
# or correct
class SubManEventDbus(dbus.service.Object):
    def __init__(self, conn, object_path='/PluginEvent'):
        dbus.service.Object.__init__(self, conn, object_path)

    # we probably want to have a proxy object of some sort so we can
    # decorate methods corresponding  to hook names, and potentially
    # pass other info as the signal payload.
    # maybe the dbus.service.Object works as a mixin and we can
    # inherit from it and SubManPlugin?
    @dbus.service.signal('com.redhat.SubscriptionManager.PluginEvent')
    def SubManPluginEvent(self, message):
        # The signal is emitted when this method exits
        # You can have code here if you wish, but the
        # decorator does the usful bits
        print("sending dbus signal with message: %s" % message)


class DbusEventPlugin(SubManPlugin):
    """Plugin to emit dbus signals for each hook"""
    name = "all_dbus"

    def __init__(self, conf=None):
        super(DbusEventPlugin, self).__init__(conf)
        # pick a bus
        self.system_bus = dbus.SystemBus()
        # choose a name for ourselves on that bus
        self.bus_name = dbus.service.BusName("com.redhat.SubscriptionManager.PluginEvent", self.system_bus)
        self.dbus_object = SubManEventDbus(self.bus_name)

    def _dbus_event(self, message, conduit):
        conduit.log.debug("sending dbus event: %s" % message)
        self.dbus_object.SubManPluginEvent(message)

    def post_facts_collection_hook(self, conduit):
        self._dbus_event("post_facts_collection", conduit)

    def pre_register_consumer_hook(self, conduit):
        self._dbus_event("pre_register_consumer", conduit)

    def post_register_consumer_hook(self, conduit):
        self._dbus_event("post_register_consumer", conduit)

    def pre_product_id_install_hook(self, conduit):
        self._dbus_event("pre_product_id_install", conduit)

    def post_product_id_install_hook(self, conduit):
        self._dbus_event("post_product_id_install", conduit)

    def pre_subscribe_hook(self, conduit):
        self._dbus_event("pre_subscribe", conduit)

    def post_subscribe_hook(self, conduit):
        self._dbus_event("post_subscribe", conduit)

    def pre_auto_attach_hook(self, conduit):
        self._dbus_event("pre_auto_attach", conduit)

    def post_auto_attach_hook(self, conduit):
        self._dbus_event("post_auto_attach", conduit)
