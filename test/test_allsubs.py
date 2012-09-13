#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import datetime
import unittest

import mock

from subscription_manager.gui import allsubs
from subscription_manager.managerlib import merge_pools

import stubs
from modelhelpers import create_pool


# need to mock Consumer identity as per mock_cleanup branch
class TestAllSubscriptionsTab(unittest.TestCase):
    def setUp(self):
        self.cert1 = stubs.StubEntitlementCertificate(
            stubs.StubProduct('product2'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2060, 1, 1),
            quantity="10", stacking_id=None)

        self.ent_cert_dir = stubs.StubCertificateDirectory([self.cert1])

        product1 = 'product1'
        product2 = 'product2'
        product_attrs = [{'name':'support_level', 'value':'Best Level'},
                         {'name':'support_type', 'value':'Best Type'}]
        pools = [
                create_pool(product1, product1, quantity=10,
                            consumed=5, productAttributes=product_attrs),
                create_pool(product1, product1, quantity=55,
                            consumed=20, productAttributes=product_attrs),
                create_pool(product2, product2, quantity=10,
                            consumed=5, productAttributes=product_attrs),
        ]
        self.merge_pools = merge_pools(pools)

        self.backend_mock = mock.Mock()
        self.consumer_mock = mock.Mock()
        self.facts_mock = mock.Mock()

        self.pool_stash_patcher = mock.patch('subscription_manager.gui.allsubs.managerlib.PoolStash')
        #merged_pools = self.ent_cert_dir.list()
        self.pool_stash_mock = self.pool_stash_patcher.start()
        self.pool_stash_mock.merge_pools = mock.Mock()
        self.pool_stash_instance = self.pool_stash_mock.return_value
        self.pool_stash_instance.merge_pools.return_value = self.merge_pools

        self.pool_stash_instance.lookup_provided_products.return_value = pools[0]['providedProducts']
        #pool_stash_mock.merge_pools.len = len(merged_pools)
        self.backend_mock.product_dir.list.return_value = []
        self.backend_mock.entitlement_dir = self.ent_cert_dir

        self.allsubs_window = allsubs.AllSubscriptionsTab(backend=self.backend_mock,
                                                          consumer=self.consumer_mock,
                                                          facts=self.facts_mock,
                                                          parent_win=None)

    def tearDown(self):
        self.pool_stash_patcher.stop()

    def test(self):

        # just show everything
        self.allsubs_window.filters.show_compatible = False
        self.allsubs_window.filters.show_no_overlapping = False
        self.allsubs_window.filters.show_installed = False
        self.allsubs_window.display_pools()

    def test_no_pools(self):
        self.pool_stash_instance.merge_pools.return_value = {}
        self.allsubs_window.display_pools()

    def test_search_button_clicked(self):
        self.allsubs_window.display_pools()
        self.allsubs_window.search_button_clicked(None)

    def test_subscribe_button_clicked(self):
        self.allsubs_window.display_pools()
        self.allsubs_window.top_view.set_cursor(self.allsubs_window.store.get_path(self.allsubs_window.store.get_iter_first()))
        self.allsubs_window.subscribe_button_clicked(None)
