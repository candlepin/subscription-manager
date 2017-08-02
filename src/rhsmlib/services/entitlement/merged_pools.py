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


class MergedPools(object):
    """
    Class to track the view of merged pools for the same product.
    Used to view total entitlement information across all pools for a
    particular product.
    """
    def __init__(self, product_id, product_name):
        self.product_id = product_id
        self.product_name = product_name
        self.bundled_products = 0
        self.quantity = 0  # how many entitlements were purchased
        self.consumed = 0  # how many are in use
        self.pools = []

    def add_pool(self, pool):
        # TODO: check if product id and name match?
        self.consumed += pool['consumed']
        # we want to add the quantity for this pool
        #  the total. if the pool is unlimited, the
        #  resulting quantity will be set to -1 and
        #  subsequent added pools will not change that.
        if pool['quantity'] == -1:
            self.quantity = -1
        elif self.quantity != -1:
            self.quantity += pool['quantity']
        self.pools.append(pool)

        # This is a little tricky, technically speaking, subscriptions
        # decide what products they provide, so it *could* vary in some
        # edge cases from one sub to another even though they are for the
        # same product. For now we'll just set this value each time a pool
        # is added and hope they are consistent.
        self.bundled_products = len(pool['providedProducts'])

    def _virt_physical_sorter(self, pool):
        """
        Used to sort the pools, return Physical or Virt depending on
        the value or existence of the virt_only attribute.

        Returning numeric values to simulate the behavior we want.
        """
        for attr in pool['attributes']:
            if attr['name'] == 'virt_only' and attr['value'] == 'true':
                return 1
        return 2

    def sort_virt_to_top(self):
        """
        Prioritizes virt pools to the front of the list, if any are present.

        Used by contract selector to show these first in the list.
        """
        self.pools.sort(key=self._virt_physical_sorter)


def merge_pools(pools):
    """
    Merges the given pools into a data structure representing the totals
    for a particular product, across all pools for that product.

    This provides an overview for a given product, how many total entitlements
    you have available and in use across all subscriptions for that product.

    Returns a dict mapping product ID to MergedPools object.
    """
    # Map product ID to MergedPools object:
    merged_pools = {}

    for pool in pools:
        if not pool['productId'] in merged_pools:
            merged_pools[pool['productId']] = MergedPools(pool['productId'],
                    pool['productName'])
        merged_pools[pool['productId']].add_pool(pool)

    # Just return a list of the MergedPools objects, without the product ID
    # key hashing:
    return merged_pools
