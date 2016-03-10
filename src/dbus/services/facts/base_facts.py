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
        properties.props_data['lastUpdatedTime'] = base_properties.Property(name='lastUpdatedTime',
                                                                        value=dbus.UInt64(0),
                                                                        value_signature='t',
                                                                        access='read')
        properties.props_data['cacheExpiryTime'] = base_properties.Property(name='cacheExpiryTime',
                                                                        value=dbus.UInt64(0),
                                                                        value_signature='t',
                                                                        access='read')
        return properties

    @slip.dbus.polkit.require_auth(constants.PK_ACTION_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=constants.FACTS_DBUS_INTERFACE,
                                   out_signature='a{ss}')
    @decorators.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        self.log.debug("GetFacts")

        # Are we using the cache or force?

        # If using the cache, load the CachedFactsCollection if possible

        # CacheCollector?
        # if cache is not expired, load the cache
        # if not cached.expired()
        #     CachedCollection has a FileCache (JsonFileCache for ex)
        #     CachedCollection.collect() would just load the file from it's cache store
        #       CachedCollection.collect calls it's self.cache.read() and returns the result
        #     facts_collection = cached.collect()

        # Return a FactsCollection that has a FactsDict
        # facts_collector is responsible for dealing with the cache

        # changed_callback that could emit a changed signal so that
        # we listen for the changed signal and save cache async?
        collection = self.facts_collector.collect()

        self.log.debug("collection=%s", collection)
        self.log.debug("collections.data=%s", collection.data)
        self.log.debug("collections.data type=%s", type(collection.data))
        # no cache comparison yet
        for i in collection:
            self.log.debug("collection i=%s", i)

        for i in collection.data:
            self.log.debug("collection.data i=%s", i)

        cleaned = dict([(str(key), str(value)) for key, value in collection.data])

        facts_dbus_dict = dbus.Dictionary(cleaned, signature="ss")

        props_iterable = [('facts', facts_dbus_dict),
                          ('lastUpdatedTime', collection.collection_datetime),
                          ('cacheExpiryTime', collection.expiry_datetime)]

        self.props._set_props(interface_name=constants.FACTS_DBUS_INTERFACE,
                              properties_iterable=props_iterable)

        return facts_dbus_dict

    # TODO: cache management
    #         - update cache (subman.facts.Facts.update_check)
    #         - delete/cleanup cache  (subman.facts.Facts.delete_cache)
    #       - signal handler for 'someone updated the facts to candlepin' (update_check, etc)
    #
    #       - facts.CheckUpdate(), emit FactsChecked() (and bool for 'yes, new facst' in signal?)
    #       - track a 'factsMayNeedToBeSyncedToCandlepin' prop?
