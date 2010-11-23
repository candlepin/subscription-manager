#
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

import hashlib

from datetime import timedelta, datetime
from certificate import DateRange
from mock import Mock

def create_pool(product_id, product_name, quantity=10, consumed=0, provided_products=[]):
    """
    Returns a hash representing a pool. Used to simulate the JSON returned
    from Candlepin.
    """
    provided = []
    for pid in provided_products:
        provided.append({'productId': pid})

    id = hashlib.md5(product_id).hexdigest()

    return {
            'productName': product_name,
            'productId': product_id,
            'quantity': quantity,
            'consumed': consumed,
            'id': id,
            'subscriptionId': '402881062bc9a379012bc9a3d7380050',
            'startDate': datetime.now() - timedelta(days=365),
            'endDate': datetime.now() + timedelta(days=365),
            'updated': datetime.now() - timedelta(days=365),
            'created': datetime.now() - timedelta(days=365),
            'activeSubscription': True,
            'providedProducts': provided,
            'sourceEntitlement': None,
            'href': '/pools/%s' % id,
            'restrictedToUsername': None,
            'owner': {
                'href': '/owners/admin',
                'id': '402881062bc9a379012bc9a393fe0005'},
            'attributes': [],
        }

def mock_product_dir(product_certs):
    """ Mock a ProductDirectory object for installed product certs. """
    installed = product_certs

    # Create the ProductDirectory mock:
    mock_product_dir = Mock()
    mock_product_dir.list.return_value = installed
    return mock_product_dir

def mock_product_cert(product_id):
    cert = Mock()
    cert.getProduct().getHash.return_value = product_id
    return cert

def mock_ent_cert(product_id, start_date=None, end_date=None):
    cert = Mock()
    cert.validRange.return_value = DateRange(start_date, end_date)
    return cert

def mock_ent_dir_no_product(ent_certs):
    """
    Mock an EntitlementDirectory object that doesn't
    find any certs for a particular product.
    """
    mock_ent_dir = Mock()
    mock_ent_dir.list.return_value = ent_certs
    mock_ent_dir.findByProduct.return_value = None
    return mock_ent_dir

def mock_ent_dir(ent_certs):
    """Mock an EntitlementDirectory object"""
    mock_ent_dir = Mock()
    mock_ent_dir.list.return_value = ent_certs
    return mock_ent_dir
