from logutil import getLogger
from managerlib import PoolFilter, merge_pools
from threading import Thread

log = getLogger(__name__)

def list_pools(uep, consumer_uuid, facts, all=False, active_on=None):
    """
    Wrapper around the UEP call to fetch pools, which forces a facts update
    if anything has changed before making the request. This ensures the
    rule checks server side will have the most up to date info about the
    consumer possible.
    """
    if facts.delta():
        uep.updateConsumerFacts(consumer_uuid, facts.get_facts())
    return uep.getPoolsList(consumer_uuid, all, active_on)

class PoolStash(object):
    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer
        self.facts = facts

        self.compatible_pools = {}

        self.incompatible_pools = {}

        self.all_pools = {}

    def refresh(self, active_on, callback):
        Thread(target=self.refresh_async, args=(active_on, callback,)).start()

    def refresh_async(self, active_on, callback):
        """
        Refresh the list of pools from the server, active on the given date.
        """
        self.all_pools = {}
        self.compatible_pools = {}
        log.debug("Refreshing pools from server...")
        for pool in list_pools(self.backend.uep,
                self.consumer.uuid, self.facts, active_on=active_on):
            self.compatible_pools[pool['id']] = pool
            self.all_pools[pool['id']] = pool

        # Filter the list of all pools, removing those we know are compatible.
        # Sadly this currently requires a second query to the server.
        self.incompatible_pools = {}
        for pool in list_pools(self.backend.uep,
                self.consumer.uuid, self.facts, all=True, active_on=active_on):
            if not pool['id'] in self.compatible_pools:
                self.incompatible_pools[pool['id']] = pool
                self.all_pools[pool['id']] = pool

        log.debug("found %s pools:" % len(self.all_pools))
        log.debug("   %s compatible" % len(self.compatible_pools))
        log.debug("   %s incompatible" % len(self.incompatible_pools))
        callback(self.compatible_pools, self.incompatible_pools, self.all_pools)

    def filter_pools(self, compatible, overlapping, uninstalled, text):
        """
        Return a list of pool hashes, filtered according to the given options.

        This method does not actually hit the server, filtering is done in
        memory.
        """
        pools = self.incompatible_pools.values()

        if compatible:
            pools = self.compatible_pools.values()

        pool_filter = PoolFilter()

        # Filter out products that are not installed if necessary:
        if uninstalled:
            pools = pool_filter.filter_out_installed(pools)
        else:
            pools = pool_filter.filter_out_uninstalled(pools)

        # Do nothing if set to None:
        if overlapping:
            pools = pool_filter.filter_out_non_overlapping(pools)
        elif overlapping == False:
            pools = pool_filter.filter_out_overlapping(pools)

        # Filter by product name if necessary:
        if text:
            pools = pool_filter.filter_product_name(pools, text)

        return pools

    def merge_pools(self, compatible=True, overlapping=None, uninstalled=False,
            text=None):
        """
        Return a merged view of pools filtered according to the given options.
        Pools for the same product will be merged into a MergedPool object.

        Overlapping filter by default is None, meaning the pools will not be
        filtered at all. Use True to filter out pools which do not overlap,
        or False to filter out pools which do.
        """
        pools = self.filter_pools(compatible, overlapping, uninstalled, text)
        merged_pools = merge_pools(pools)
        return merged_pools
