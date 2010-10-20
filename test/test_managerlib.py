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

import unittest
from mock import Mock

from managerlib import *
from jsonhelpers import *

class MergePoolsTests(unittest.TestCase):

    def test_single_pool(self):
        facts = Mock()
        product = 'product1'
        pools = [
                create_pool(product, product, quantity=10, consumed=5)
        ]
        results = merge_pools(pools)
        self.assertEquals(1, len(results.values()))
        result = results.values()[0]
        self.assertEquals(product, result.product_id)

    def test_multiple_pools(self):
        facts = Mock()
        product1 = 'product1'
        product2 = 'product2'
        pools = [
                create_pool(product1, product1, quantity=10, consumed=5),
                create_pool(product1, product1, quantity=55, consumed=20),
                create_pool(product2, product2, quantity=10, consumed=5),
        ]
        results = merge_pools(pools)
        self.assertEquals(2, len(results.values()))
        self.assertTrue(results.has_key(product1))
        self.assertTrue(results.has_key(product2))

        # Check product1:
        merged_pools = results[product1]
        self.assertEquals(product1, merged_pools.product_id)
        self.assertEquals(65, merged_pools.quantity)
        self.assertEquals(25, merged_pools.consumed)

        # Check product2:
        merged_pools = results[product2]
        self.assertEquals(product2, merged_pools.product_id)
        self.assertEquals(10, merged_pools.quantity)
        self.assertEquals(5, merged_pools.consumed)
