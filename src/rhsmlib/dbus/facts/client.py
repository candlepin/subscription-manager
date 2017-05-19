from __future__ import print_function, division, absolute_import

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
import dbus

from rhsmlib.dbus.facts import constants as facts_constants

log = logging.getLogger(__name__)


class FactsClientAuthenticationError(Exception):
    def __init__(self, *args, **kwargs):
        action_id = kwargs.pop("action_id")
        super(FactsClientAuthenticationError, self).__init__(*args, **kwargs)
        log.debug("FactsClientAuthenticationError created for %s", action_id)
        self.action_id = action_id


class FactsClient(object):
    bus_name = facts_constants.FACTS_DBUS_NAME
    object_path = facts_constants.FACTS_DBUS_PATH
    interface_name = facts_constants.FACTS_DBUS_INTERFACE

    def __init__(self, bus=None, bus_name=None, object_path=None, interface_name=None):
        self.bus = bus or dbus.SystemBus()

        if bus_name:
            self.bus_name = bus_name

        if object_path:
            self.object_path = object_path

        if interface_name:
            self.interface_name = interface_name

        self.dbus_proxy_object = self.bus.get_object(self.bus_name, self.object_path,
            follow_name_owner_changes=True)

        self.interface = dbus.Interface(self.dbus_proxy_object,
            dbus_interface=self.interface_name)

        self.bus.call_on_disconnection(self._on_bus_disconnect)

    def GetFacts(self, *args, **kwargs):
        return self.interface.GetFacts(*args, **kwargs)

    def _on_bus_disconnect(self, connection):
        self.dbus_proxy_object = None
        log.debug("Disconnected from FactsService")
