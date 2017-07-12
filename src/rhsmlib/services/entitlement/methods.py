from __future__ import print_function, division, absolute_import

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

from subscription_manager.injection import require, CERT_SORTER, \
        IDENTITY, ENTITLEMENT_STATUS_CACHE, \
        PROD_STATUS_CACHE, ENT_DIR, PROD_DIR, CP_PROVIDER, OVERRIDE_STATUS_CACHE, \
        POOLTYPE_CACHE, RELEASE_STATUS_CACHE, FACTS, POOL_STATUS_CACHE

from .pool_stash import PoolStash
from subscription_manager.jsonwrapper import PoolWrapper

# This method is morphing the actual pool json and returning a new
# dict which does not contain all the pool info. Not sure if this is really
# necessary. Also some "view" specific things going on in here.

def get_available_entitlements(get_all=False, active_on=None, overlapping=False,
                               uninstalled=False, text=None, filter_string=None):
    """
    Returns a list of entitlement pools from the server.

    The 'all' setting can be used to return all pools, even if the rules do
    not pass. (i.e. show pools that are incompatible for your hardware)
    """
    columns = [
        'id',
        'quantity',
        'consumed',
        'endDate',
        'productName',
        'providedProducts',
        'productId',
        'attributes',
        'pool_type',
        'service_level',
        'service_type',
        'suggested',
        'contractNumber',
        'management_enabled'
    ]

    pool_stash = PoolStash()
    dlist = pool_stash.get_filtered_pools_list(active_on, not get_all,
           overlapping, uninstalled, text, filter_string)

    for pool in dlist:
        pool_wrapper = PoolWrapper(pool)
        pool['providedProducts'] = pool_wrapper.get_provided_products()
        if allows_multi_entitlement(pool):
            pool['multi-entitlement'] = "Yes"
        else:
            pool['multi-entitlement'] = "No"

        support_attrs = pool_wrapper.get_product_attributes("support_level",
                                                            "support_type")
        pool['service_level'] = support_attrs['support_level']
        pool['service_type'] = support_attrs['support_type']
        pool['suggested'] = pool_wrapper.get_suggested_quantity()
        pool['pool_type'] = pool_wrapper.get_pool_type()
        pool['management_enabled'] = pool_wrapper.management_enabled()

        if pool['suggested'] is None:
            pool['suggested'] = ""

    # no default, so default is None if key not found
    data = [_sub_dict(pool, columns) for pool in dlist]
    for d in data:
        if int(d['quantity']) < 0:
            d['quantity'] = _('Unlimited')
        else:
            d['quantity'] = str(int(d['quantity']) - int(d['consumed']))

        d['endDate'] = format_date(isodate.parse_date(d['endDate']))
        del d['consumed']

    return data


