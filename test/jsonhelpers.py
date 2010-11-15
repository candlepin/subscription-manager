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

from datetime import timedelta, datetime

def create_pool(product_id, product_name, quantity=10, consumed=0, provided_products=[]):
    """
    Returns a hash representing a pool. Used to simulate the JSON returned
    from Candlepin.
    """
    provided = []
    for pid in provided_products:
        provided.append({'productId': pid})

    return {
            'productName': product_name,
            'productId': product_id,
            'quantity': quantity,
            'consumed': consumed,
            'id': '402881062bc9a379012bc9a4095c00c9',
            'subscriptionId': '402881062bc9a379012bc9a3d7380050',
            'startDate': datetime.now() - timedelta(days=365),
            'endDate': datetime.now() + timedelta(days=365),
            'updated': datetime.now() - timedelta(days=365),
            'created': datetime.now() - timedelta(days=365),
            'activeSubscription': True,
            'providedProducts': provided,
            'sourceEntitlement': None,
            'href': '/pools/402881062bc9a379012bc9a4095c00c9',
            'restrictedToUsername': None,
            'owner': {
                'href': '/owners/admin',
                'id': '402881062bc9a379012bc9a393fe0005'},
            'attributes': [],
        }
