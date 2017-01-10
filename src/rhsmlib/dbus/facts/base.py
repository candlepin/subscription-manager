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
import os
import logging
import dbus

import rhsm.config

from rhsmlib.facts import collector, host_collector, hwprobe, custom
from rhsmlib.dbus import util, base_object
from rhsmlib.dbus.facts import constants

log = logging.getLogger(__name__)


class BaseFacts(base_object.BaseObject):
    interface_name = constants.FACTS_DBUS_INTERFACE
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
        cleaned = dict([(str(key), str(value)) for key, value in collection.data.items()])
        return dbus.Dictionary(cleaned, signature="ss")


class AllFacts(base_object.BaseObject):
    interface_name = constants.FACTS_DBUS_INTERFACE
    default_dbus_path = constants.FACTS_DBUS_PATH

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(AllFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        # Why aren't we using a dictionary here? Because we want to control the order and OrderedDict
        # isn't in Python 2.6.  By controlling the order and putting CustomFacts last, we can ensure
        # that users can override any fact.
        collector_definitions = [
            ("Host", HostFacts),
            ("Hardware", HardwareFacts),
            ("Static", StaticFacts),
            ("Custom", CustomFacts),
        ]

        self.collectors = []
        for path, clazz in collector_definitions:
            sub_path = self.default_dbus_path + "/" + path
            self.collectors.append(
                (path, clazz(conn=conn, object_path=sub_path, bus_name=bus_name))
            )

    @util.dbus_service_method(
        dbus_interface=constants.FACTS_DBUS_INTERFACE,
        out_signature='a{ss}')
    @util.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        results = {}
        for name, fact_collector in self.collectors:
            results.update(fact_collector.GetFacts())
        return dbus.Dictionary(results, signature="ss")

    def remove_from_connection(self, connection=None, path=None):
        # Call remove_from_connection on all the child objects first
        for sub_path, obj in self.collectors:
            if path:
                child_path = path + "/" + sub_path
            else:
                child_path = None
            obj.remove_from_connection(connection, child_path)
        super(AllFacts, self).remove_from_connection(connection, path)


class HostFacts(BaseFacts):
    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(HostFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.facts_collector = host_collector.HostCollector()


class HardwareFacts(BaseFacts):
    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(HardwareFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.facts_collector = hwprobe.HardwareCollector()


class CustomFacts(BaseFacts):
    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(CustomFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        paths_and_globs = [
            (os.path.join(rhsm.config.DEFAULT_CONFIG_DIR, 'facts'), '*.facts'),
        ]
        self.facts_collector = custom.CustomFactsCollector(path_and_globs=paths_and_globs)


class StaticFacts(BaseFacts):
    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(StaticFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.facts_collector = collector.StaticFactsCollector({
            "system.certificate_version": constants.CERT_VERSION
        })
