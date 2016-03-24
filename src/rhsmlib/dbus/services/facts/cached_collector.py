import logging

from rhsmlib.facts import collection
from rhsmlib.facts import collector

# TODO: mv to common or services/?
from rhsmlib.dbus.services.facts import cache
from rhsmlib.dbus.services.facts import expiration

log = logging.getLogger(__name__)


class CachedFactsCollector(collector.FactsCollector):
    def __init__(self, arch=None, prefix=None, testing=None,
                 hardware_methods=None, collected_hw_info=None, collectors=None,
                 cache=None):
        super(CachedFactsCollector, self).__init__(arch=arch, prefix=prefix, testing=testing,
                                                   hardware_methods=hardware_methods,
                                                   collected_hw_info=collected_hw_info,
                                                   collectors=collectors)
        self.cache = cache
        # On creation, a Cached collector is dirty until it is persisted.
        # If it created from a cache, then dirty is flipped to false.
        self.dirty = True

    def cache_save_start(self, facts_collection):
        # Create a new Cached FactsCollection with new timestamp
        # cached
        log.debug("save_to_cache facts_collection=%s", facts_collection)

        #self.cache.write(dict(cached_facts.data))

    def cache_save_finished(self, facts_collection):
        log.debug("cache_save_finished facts_collection=%s", facts_collection)

    def collect(self):
        log.debug("duration=%s", cache.expiration.duration_seconds)
        # A new expiration, of the same duration, but starting now.
        host_facts_expiration = expiration.Expiration(duration_seconds=self.cache.expiration.duration_seconds)
        fresh_collection = collection.FactsCollection(expiration=host_facts_expiration)

        try:
            cached_collection = collection.FactsCollection.from_cache(self.cache)
        except cache.CacheError as e:
            log.exception(e)
            cached_collection = None

        new_enough_collection = cached_collection.merge(fresh_collection)

        # Most of the time, we still haven't collected any facts yet.
        # Until we iterate over fresh_facts, does it's iter start collection

        # FIXME: This could wait until we get the facts property change signal?
        self.cache_save_start(new_enough_collection)

        return fresh_collection
        #return self.collection
