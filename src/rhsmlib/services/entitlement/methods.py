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

from subscription_manager import injection as inj

from .pool_wrapper import PoolWrapper
from subscription_manager import isodate
from dateutil.tz import tzlocal

import logging
log = logging.getLogger(__name__)


def format_date(dt):
    if not dt:
        return ""
    try:
        return dt.astimezone(tzlocal()).strftime("%x")
    except ValueError:
        log.warn("Datetime does not contain timezone information")
        return dt.strftime("%x")


def _sub_dict(datadict, subkeys, default=None):
    """Return a dict that is a subset of datadict matching only the keys in subkeys"""
    return dict([(k, datadict.get(k, default)) for k in subkeys])


def is_true_value(test_string):
    val = str(test_string).lower()
    return val == "1" or val == "true" or val == "yes"


def allows_multi_entitlement(pool):
    """
    Determine if this pool allows multi-entitlement based on the pool's
    top-level product's multi-entitlement attribute.
    """
    for attribute in pool['productAttributes']:
        if attribute['name'] == "multi-entitlement" and \
            is_true_value(attribute['value']):
            return True
    return False


# This method is morphing the actual pool json and returning a new
# dict which does not contain all the pool info. Not sure if this is really
# necessary. Also some "view" specific things going on in here.


def get_available_entitlements(get_all=False, active_on=None, overlapping=False,
                               uninstalled=False, text=None, filter_string=None, **kwargs):
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

    #
    # FIXME
    # Since Register using DBus is not implemented yet,
    # it is necessary to reload identity before candlepin call.
    #
    inj.require(inj.IDENTITY).reload()

    dlist = inj.require(inj.POOL_STASH).get_filtered_pools_list(
        active_on, not get_all, overlapping, uninstalled, text, filter_string)

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
            d['quantity'] = 'Unlimited'
        else:
            d['quantity'] = str(int(d['quantity']) - int(d['consumed']))

        d['endDate'] = format_date(isodate.parse_date(d['endDate']))
        del d['consumed']

    return data
