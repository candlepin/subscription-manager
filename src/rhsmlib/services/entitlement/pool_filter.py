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

from subscription_manager import isodate
from .pool_wrapper import PoolWrapper

import logging

log = logging.getLogger(__name__)


class PoolFilter(object):
    """
    Helper to filter a list of pools.
    """
    # Although sorter isn't necessarily required, when present it allows
    # us to not filter out yellow packages when "has no overlap" is selected
    def __init__(self, product_dir, entitlement_dir, sorter=None):

        self.product_directory = product_dir
        self.entitlement_directory = entitlement_dir
        self.sorter = sorter

    def filter_product_ids(self, pools, product_ids):
        """
        Filter a list of pools and return just those that provide products
        in the requested list of product ids. Both the top level product
        and all provided products will be checked.
        """
        matched_pools = []
        for pool in pools:
            if pool['productId'] in product_ids:
                log.debug("pool matches: %s" % pool['productId'])
                matched_pools.append(pool)
                continue

            for provided in pool['providedProducts']:
                if provided['productId'] in product_ids:
                    log.debug("pool provides: %s" % provided['productId'])
                    matched_pools.append(pool)
                    break
        return matched_pools

    def filter_out_uninstalled(self, pools):
        """
        Filter the given list of pools, return only those which provide
        a product installed on this system.
        """
        installed_products = self.product_directory.list()
        matched_data_dict = {}
        for d in pools:
            for product in installed_products:
                productid = product.products[0].id
                # we only need one matched item per pool id, so add to dict to keep unique:
                # Build a list of provided product IDs for comparison:
                provided_ids = [p['productId'] for p in d['providedProducts']]

                if str(productid) in provided_ids or \
                        str(productid) == d['productId']:
                    matched_data_dict[d['id']] = d

        return list(matched_data_dict.values())

    def filter_out_installed(self, pools):
        """
        Filter the given list of pools, return only those which do not provide
        a product installed on this system.
        """
        installed_products = self.product_directory.list()
        matched_data_dict = {}
        for d in pools:
            matched_data_dict[d['id']] = d
            provided_ids = [p['productId'] for p in d['providedProducts']]
            for product in installed_products:
                productid = product.products[0].id
                # we only need one matched item per pool id, so add to dict to keep unique:
                if str(productid) in provided_ids or \
                        str(productid) == d['productId']:
                    del matched_data_dict[d['id']]
                    break

        return list(matched_data_dict.values())

    def filter_product_name(self, pools, contains_text):
        """
        Filter the given list of pools, removing those whose product name
        does not contain the given text.
        """
        lowered = contains_text.lower()
        filtered_pools = []
        for pool in pools:
            if lowered in pool['productName'].lower():
                filtered_pools.append(pool)
            else:
                for provided in pool['providedProducts']:
                    if lowered in provided['productName'].lower():
                        filtered_pools.append(pool)
                        break
        return filtered_pools

    def _get_entitled_product_ids(self):
        entitled_products = []
        for cert in self.entitlement_directory.list():
            for product in cert.products:
                entitled_products.append(product.id)
        return entitled_products

    def _get_entitled_product_to_cert_map(self):
        entitled_products_to_certs = {}
        for cert in self.entitlement_directory.list():
            for product in cert.products:
                prod_id = product.id
                if prod_id not in entitled_products_to_certs:
                    entitled_products_to_certs[prod_id] = set()
                entitled_products_to_certs[prod_id].add(cert)
        return entitled_products_to_certs

    def _dates_overlap(self, pool, certs):
        pool_start = isodate.parse_date(pool['startDate'])
        pool_end = isodate.parse_date(pool['endDate'])

        for cert in certs:
            cert_range = cert.valid_range
            if cert_range.has_date(pool_start) or cert_range.has_date(pool_end):
                return True
        return False

    def filter_out_overlapping(self, pools):
        entitled_product_ids_to_certs = self._get_entitled_product_to_cert_map()
        filtered_pools = []
        for pool in pools:
            provided_ids = set([p['productId'] for p in pool['providedProducts']])
            wrapped_pool = PoolWrapper(pool)
            # NOTE: We may have to check for other types or handle the case of a product with no type in the future
            if wrapped_pool.get_product_attributes('type')['type'] == 'SVC':
                provided_ids.add(pool['productId'])
            overlap = 0
            possible_overlap_pids = provided_ids.intersection(list(entitled_product_ids_to_certs.keys()))
            for productid in possible_overlap_pids:
                if self._dates_overlap(pool, entitled_product_ids_to_certs[productid]) \
                        and productid not in self.sorter.partially_valid_products:
                    overlap += 1
                else:
                    break
            if overlap != len(provided_ids) or wrapped_pool.get_stacking_id() in self.sorter.partial_stacks:
                filtered_pools.append(pool)

        return filtered_pools

    def filter_out_non_overlapping(self, pools):
        not_overlapping = self.filter_out_overlapping(pools)
        return [pool for pool in pools if pool not in not_overlapping]

    def filter_subscribed_pools(self, pools, subscribed_pool_ids,
            compatible_pools):
        """
        Filter the given list of pools, removing those for which the system
        already has a subscription, unless the pool can be subscribed to again
        (ie has multi-entitle).
        """
        resubscribeable_pool_ids = [pool['id'] for pool in
                                    list(compatible_pools.values())]

        filtered_pools = []
        for pool in pools:
            if (pool['id'] not in subscribed_pool_ids) or \
                    (pool['id'] in resubscribeable_pool_ids):
                filtered_pools.append(pool)
        return filtered_pools
