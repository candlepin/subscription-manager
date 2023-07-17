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
from typing import TYPE_CHECKING, Dict, Type

import dbus

from rhsmlib.facts import collector, host_collector, hwprobe, custom, all
from rhsmlib.facts.collector import FactsCollector
from rhsmlib.dbus import util, base_object
from rhsmlib.dbus.facts import constants

if TYPE_CHECKING:
    from rhsmlib.facts.collection import FactsCollection

log = logging.getLogger(__name__)


class FactsImplementation(base_object.BaseImplementation):
    def __init__(self, collector_class: Type["FactsCollector"]):
        self.collector: FactsCollector = collector_class()

    def get_facts(self) -> Dict[str, str]:
        collection: FactsCollection = self.collector.collect()
        cleaned = dict([(str(key), str(value)) for key, value in list(collection.data.items())])
        return cleaned


class BaseFacts(base_object.BaseObject):
    interface_name = constants.FACTS_DBUS_INTERFACE
    default_dbus_path = constants.FACTS_DBUS_PATH
    default_props_data = {}
    collector_class: Type[FactsCollector] = collector.FactsCollector

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super().__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.impl = FactsImplementation(self.collector_class)

    @util.dbus_service_method(
        dbus_interface=constants.FACTS_DBUS_INTERFACE,
        out_signature="a{ss}",
    )
    @util.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        facts = self.impl.get_facts()
        return dbus.Dictionary(facts, signature="ss")


class AllFacts(BaseFacts):
    collector_class = all.AllFactsCollector


class HostFacts(BaseFacts):
    collector_class = host_collector.HostCollector


class HardwareFacts(BaseFacts):
    collector_class = hwprobe.HardwareCollector


class CustomFacts(BaseFacts):
    collector_class = custom.CustomFactsCollector


class StaticFacts(BaseFacts):
    collector_class = collector.StaticFactsCollector
