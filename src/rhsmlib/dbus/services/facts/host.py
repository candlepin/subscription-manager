
import logging

from rhsmlib.facts import host_collector

from rhsmlib.dbus.services.facts import cache
from rhsmlib.dbus.services.facts import constants
from rhsmlib.dbus.services.facts import base_facts

log = logging.getLogger(__name__)


class FactsHostCacheFile(cache.JsonFileCache):
    CACHE_FILE = constants.FACTS_HOST_CACHE_FILE
    default_duration_seconds = constants.FACTS_HOST_CACHE_DURATION


class FactsHost(base_facts.BaseFacts):
    default_polkit_auth_required = constants.PK_ACTION_FACTS_COLLECT
    persistent = True
    default_props_data = {'version': constants.FACTS_HOST_VERSION,
                          'answer': '42',
                          'name': constants.FACTS_HOST_NAME,
                          'polkit_auth_action': constants.PK_ACTION_FACTS_COLLECT,
                          'last_update': 'before now, probably'}
    default_dbus_path = constants.FACTS_HOST_DBUS_PATH
    _service_name = constants.SUB_SERVICE_NAME

    def __init__(self, conn=None, object_path=None, bus_name=None,
                 base_object_path=None):
        super(FactsHost, self).__init__(conn=conn, object_path=object_path,
                                        bus_name=bus_name,
                                        base_object_path=base_object_path)

        host_cache = FactsHostCacheFile()
        self.facts_collector = host_collector.HostCollector(cache=host_cache)
