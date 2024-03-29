# Copyright (c) 2010 Red Hat, Inc.
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

"""
Helper methods for mocking up JSON model objects, certificates, etc.
"""
from datetime import timedelta, datetime

from rhsm.certificate import GMT

import hashlib


def md5sum(buf):
    if isinstance(buf, str):
        buf = buf.encode("utf-8")
    md = hashlib.md5(buf)
    return md.hexdigest()


def create_pool(
    product_id,
    product_name,
    quantity=10,
    consumed=0,
    provided_products=None,
    attributes=None,
    productAttributes=None,
    calculatedAttributes=None,
    start_end_range=None,
):
    """
    Returns a hash representing a pool. Used to simulate the JSON returned
    from Candlepin.
    """
    provided_products = provided_products or []
    attributes = attributes or []
    productAttributes = productAttributes or []
    start_date = datetime.now(GMT()) - timedelta(days=365)
    end_date = datetime.now(GMT()) + timedelta(days=365)
    if start_end_range:
        start_date = start_end_range.begin()
        end_date = start_end_range.end()

    provided = []
    for pid in provided_products:
        provided.append(
            {
                "productId": pid,
                "productName": pid,
            }
        )

    pool_id = md5sum(product_id)

    to_return = {
        "productName": product_name,
        "productId": product_id,
        "quantity": quantity,
        "consumed": consumed,
        "id": pool_id,
        "subscriptionId": "402881062bc9a379012bc9a3d7380050",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "updated": start_date.isoformat(),
        "created": start_date.isoformat(),
        "activeSubscription": True,
        "providedProducts": provided,
        "sourceEntitlement": None,
        "href": "/pools/%s" % pool_id,
        "restrictedToUsername": None,
        "owner": {"href": "/owners/admin", "id": "402881062bc9a379012bc9a393fe0005"},
        "attributes": attributes,
        "productAttributes": productAttributes,
    }

    if calculatedAttributes is not None:
        to_return["calculatedAttributes"] = calculatedAttributes

    return to_return


def create_attribute_list(attribute_map):
    attribute_list = []
    for name, value in attribute_map.items():
        attribute_props = {}
        attribute_props["name"] = name
        attribute_props["value"] = value
        # Add others if required
        attribute_list.append(attribute_props)
    return attribute_list
