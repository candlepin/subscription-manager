import logging

from rhsm.facts import collection
from rhsm.facts import collector

# TODO: mv to common or services/?
from rhsm.dbus.services.facts import cache
from rhsm.dbus.services.facts import constants

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

    def save_to_cache(self, facts_collection):
        # Create a new FactsCollection with new timestamp
        cached_facts = collection.FactsCollection.from_facts_collection(facts_collection)
        self.cache.write(cached_facts.data)

    def collect(self):
        fresh_collection = collection.FactsCollection()

        try:
            cached_collection = collection.FactsCollection.from_cache(self.cache,
                                                                      constants.FACTS_HOST_CACHE_DURATION)
        except cache.CacheError as e:
            log.exception(e)
            cached_collection = None

        # not really '==', but more of a 'close-enough-to-equals', ie
        # the cache isn't expired, so don't bother looking any closer.
        #
        #
        # Should be able to compare None == facts_collection
        if cached_collection == fresh_collection:
            return cached_collection

        # replace with an iterator
        facts_dict = collection.FactsDict()
        facts_dict.update(self.get_all())
        fresh_collection.data = facts_dict
        # Most of the time, we still haven't collected any facts yet.
        # Until we iterate over fresh_facts, does it's iter start collection

        # FIXME: This could wait until we get the facts property change signal?
        self.save_to_cache(fresh_collection)

        return fresh_collection
        #return self.collection
