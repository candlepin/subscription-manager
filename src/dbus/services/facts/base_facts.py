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
    _default_facts_collector_class = collector.FactsCollector

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(BaseFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        # Default is an empty FactsCollector
        self.facts_collector = self._default_facts_collector_class()

    def _create_props(self):
        properties = base_properties.BaseProperties.from_string_to_string_dict(self._interface_name,
                                                                               self.default_props_data,
                                                                               self.PropertiesChanged)
        properties.props_data['facts'] = base_properties.Property(name='facts',
                                                                  value=dbus.Dictionary({}, signature='ss'),
                                                                  value_signature='a{ss}',
                                                                  access='read')
        return properties

    @slip.dbus.polkit.require_auth(constants.PK_ACTION_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=constants.FACTS_DBUS_INTERFACE,
                                   out_signature='a{ss}')
    @decorators.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        # Return a FactsCollection that has a FactsDict
        collection = self.facts_collector.collect()

        self.log.debug("collection=%s", collection)
        self.log.debug("collections.data=%s", collection.data)
        # no cache comparison yet

        cleaned = dict([(str(key), str(value)) for key, value in collection.data.items()])

        facts_dbus_dict = dbus.Dictionary(cleaned, signature="ss")

        self.props._set(interface_name=constants.FACTS_DBUS_INTERFACE,
                        property_name='facts',
                        new_value=facts_dbus_dict)
        return facts_dbus_dict

    # TODO: cache management
    #         - update cache (subman.facts.Facts.update_check)
    #         - delete/cleanup cache  (subman.facts.Facts.delete_cache)
    #       - signal handler for 'someone updated the facts to candlepin' (update_check, etc)
    #
    #       - facts.CheckUpdate(), emit FactsChecked() (and bool for 'yes, new facst' in signal?)
    #       - track a 'factsMayNeedToBeSyncedToCandlepin' prop?
