from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
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

from rhsmlib.facts import collector, host_collector, hwprobe, custom, all
from rhsmlib.dbus import util, base_object
from rhsmlib.dbus.facts import constants

log = logging.getLogger(__name__)


class BaseFacts(base_object.BaseObject):
    interface_name = constants.FACTS_DBUS_INTERFACE
    default_dbus_path = constants.FACTS_DBUS_PATH
    default_props_data = {}
    facts_collector_class = collector.FactsCollector

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(BaseFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        # Default is an empty FactsCollector
        self.facts_collector = self.facts_collector_class()

    @util.dbus_service_method(
        dbus_interface=constants.FACTS_DBUS_INTERFACE,
        out_signature='a{ss}')
    @util.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        collection = self.facts_collector.collect()
        cleaned = dict([(str(key), str(value)) for key, value in list(collection.data.items())])
        return dbus.Dictionary(cleaned, signature="ss")


def class_factory(name, facts_collector=None):
    """Function used for creating subclasses of class BaseFact"""
    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(self.__class__, self).__init__(conn=conn,
                                             object_path=object_path,
                                             bus_name=bus_name)
        self.facts_collector = facts_collector
    return type(name, (BaseFacts,), {"__init__": __init__})


AllFacts = class_factory('AllFacts', all.AllFactsCollector())
HostFacts = class_factory('HostFacts', host_collector.HostCollector())
HardwareFacts = class_factory('HardwareFacts', hwprobe.HardwareCollector())
CustomFacts = class_factory('CustomFacts', custom.CustomFactsCollector())
StaticFacts = class_factory('StaticFacts', collector.StaticFactsCollector())
