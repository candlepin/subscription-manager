import logging

import dbus
import slip.dbus

from rhsm.facts import collector
from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_properties
from rhsm.dbus.services import base_service
from rhsm.dbus.services.facts import constants

log = logging.getLogger(__name__)


class BaseFacts(base_service.BaseService):
    _interface_name = constants.FACTS_DBUS_INTERFACE
    facts_collector_class = collector.FactsCollector

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(BaseFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        # Default is an empty FactsCollector
        self.facts_collector = self.facts_collector_class()

    def _create_props(self):
        return base_properties.BaseProperties(self._interface_name,
                                              data=self.default_props_data,
                                              properties_changed_callback=self.PropertiesChanged)

    @slip.dbus.polkit.require_auth(constants.PK_ACTION_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=constants.FACTS_DBUS_INTERFACE,
                                   out_signature='a{ss}')
    @decorators.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        facts_dict = self.facts_collector.get_all()
        cleaned = dict([(str(key), str(value)) for key, value in facts_dict.items()])
        dbus_dict = dbus.Dictionary(cleaned, signature="ss")
        return dbus_dict
