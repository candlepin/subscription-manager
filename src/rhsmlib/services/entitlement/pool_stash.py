from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2017 Red Hat, Inc.
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
log = logging.getLogger(__name__)
from .pool_filter import PoolFilter

from subscription_manager.injection import require, CERT_SORTER, \
    COMPLIANCE_MANAGER_FACTORY, IDENTITY, ENTITLEMENT_STATUS_CACHE, \
    PROD_STATUS_CACHE, ENT_DIR, PROD_DIR, CP_PROVIDER, OVERRIDE_STATUS_CACHE, \
    POOLTYPE_CACHE, RELEASE_STATUS_CACHE, FACTS, POOL_STATUS_CACHE, \
    PROFILE_MANAGER

class PoolStash(object):
    """
    Object used to fetch pools from the server, sort them into compatible,
    incompatible, and installed lists. Also does filtering based on name.
    """
    def __init__(self):
        self.identity = require(IDENTITY)
        self.sorter = None

        # Pools which passed rules server side for this consumer:
        self.compatible_pools = {}

        # Pools which failed a rule check server side:
        self.incompatible_pools = {}

        # Pools for which we already have an entitlement:
        self.subscribed_pool_ids = []

        # All pools:
        self.all_pools = {}

    def all_pools_size(self):
        return len(self.all_pools)

    def refresh(self, active_on):
        """
        Refresh the list of pools from the server, active on the given date.
        """

        self.sorter = active_on and require(COMPLIANCE_MANAGER_FACTORY)(on_date=active_on) \
                      or require(CERT_SORTER)

        self.all_pools = {}
        self.compatible_pools = {}
        log.debug("Refreshing pools from server...")
        for pool in list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid, active_on=active_on):
            self.compatible_pools[pool['id']] = pool
            self.all_pools[pool['id']] = pool

        # Filter the list of all pools, removing those we know are compatible.
        # Sadly this currently requires a second query to the server.
        self.incompatible_pools = {}
        for pool in list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid, list_all=True, active_on=active_on):
            if not pool['id'] in self.compatible_pools:
                self.incompatible_pools[pool['id']] = pool
                self.all_pools[pool['id']] = pool

        self.subscribed_pool_ids = self._get_subscribed_pool_ids()

        # In the gui, cache all pool types so when we attach new ones
        # we can avoid more api calls
        require(POOLTYPE_CACHE).update_from_pools(self.all_pools)

        log.debug("found %s pools:" % len(self.all_pools))
        log.debug("   %s compatible" % len(self.compatible_pools))
        log.debug("   %s incompatible" % len(self.incompatible_pools))
        log.debug("   %s already subscribed" % len(self.subscribed_pool_ids))

    def get_filtered_pools_list(self, active_on, incompatible,
            overlapping, uninstalled, text, filter_string):
        """
        Used for CLI --available filtering
        cuts down on api calls
        """
        self.all_pools = {}
        self.compatible_pools = {}
        if active_on and overlapping:
            self.sorter = ComplianceManager(active_on)
        elif not active_on and overlapping:
            self.sorter = require(CERT_SORTER)

        if incompatible:
            for pool in self.list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                    self.identity.uuid, active_on=active_on, filter_string=filter_string):
                self.compatible_pools[pool['id']] = pool
        else:  # --all has been used
            for pool in self.list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                    self.identity.uuid, list_all=True, active_on=active_on, filter_string=filter_string):
                self.all_pools[pool['id']] = pool

        return self._filter_pools(incompatible, overlapping, uninstalled, False, text)

    def _get_subscribed_pool_ids(self):
        return [ent.pool.id for ent in require(ENT_DIR).list()]

    def _filter_pools(self, incompatible, overlapping, uninstalled, subscribed,
            text):
        """
        Return a list of pool hashes, filtered according to the given options.

        This method does not actually hit the server, filtering is done in
        memory.
        """

        log.debug("Filtering %d total pools" % len(self.all_pools))
        if not incompatible:
            pools = list(self.all_pools.values())
        else:
            pools = list(self.compatible_pools.values())
            log.debug("\tRemoved %d incompatible pools" %
                       len(self.incompatible_pools))

        pool_filter = PoolFilter(require(PROD_DIR),
                require(ENT_DIR), self.sorter)

        # Filter out products that are not installed if necessary:
        if uninstalled:
            prev_length = len(pools)
            pools = pool_filter.filter_out_uninstalled(pools)
            log.debug("\tRemoved %d pools for not installed products" %
                       (prev_length - len(pools)))

        if overlapping:
            prev_length = len(pools)
            pools = pool_filter.filter_out_overlapping(pools)
            log.debug("\tRemoved %d pools overlapping existing entitlements" %
                      (prev_length - len(pools)))

        # Filter by product name if necessary:
        if text:
            prev_length = len(pools)
            pools = pool_filter.filter_product_name(pools, text)
            log.debug("\tRemoved %d pools not matching the search string" %
                      (prev_length - len(pools)))

        if subscribed:
            prev_length = len(pools)
            pools = pool_filter.filter_subscribed_pools(pools,
                    self.subscribed_pool_ids, self.compatible_pools)
            log.debug("\tRemoved %d pools that we're already subscribed to" %
                      (prev_length - len(pools)))

        log.debug("\t%d pools to display, %d filtered out" % (len(pools),
            len(self.all_pools) - len(pools)))

        return pools

    def list_pools(self,uep, consumer_uuid, list_all=False, active_on=None, filter_string=None):
        """
        Wrapper around the UEP call to fetch pools, which forces a facts update
        if anything has changed before making the request. This ensures the
        rule checks server side will have the most up to date info about the
        consumer possible.
        """

        # client tells service 'look for facts again'
        # if service finds new facts:
        #     -emit a signal?
        #     - or just update properties
        #       - and set a 'been_synced' property to False
        # client waits for facts check to finish
        # if no changes or been_synced=True, continue
        # if changes or unsynced:
        #    subman updates candlepin with the latest version of services GetFacts() [blocking]
        #    when finished, subman emit's 'factsSyncFinished'
        #        - then service flops 'been_synced' property
        #    -or- subman calls 'here_are_the_latest_facts_to_the_server()' on service
        #         then service flops 'been_synced' property
        # subman gets signal that props changed, and that been_synced is now true
        # since it's been synced, then subman continues
        require(FACTS).update_check(uep, consumer_uuid)
        require(PROFILE_MANAGER).update_check(uep, consumer_uuid)

        owner = uep.getOwner(consumer_uuid)
        ownerid = owner['key']

        return uep.getPoolsList(consumer=consumer_uuid, listAll=list_all,
                                active_on=active_on, owner=ownerid, filter_string=filter_string)

    def merge_pools(self, incompatible=False, overlapping=False,
            uninstalled=False, subscribed=False, text=None):
        """
        Return a merged view of pools filtered according to the given options.
        Pools for the same product will be merged into a MergedPool object.

        Arguments turn on filters, so setting one to True will reduce the
        number of results.
        """
        pools = self._filter_pools(incompatible, overlapping, uninstalled,
                subscribed, text)
        merged_pools = merge_pools(pools)
        return merged_pools

    def lookup_provided_products(self, pool_id):
        """
        Return a list of tuples (product name, product id) for all products
        provided for a given pool. If we do not actually have any info on this
        pool, return None.
        """
        pool = self.all_pools.get(pool_id)
        if pool is None:
            log.debug("pool id %s not found in all_pools", pool_id)
            return None

        provided_products = []
        for product in pool['providedProducts']:
            provided_products.append((product['productName'], product['productId']))
        return provided_products
