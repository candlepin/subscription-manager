# Copyright (c) 2011 Red Hat, Inc.
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
import datetime
from mock import Mock
from stubs import StubUEP, StubEntitlementCertificate, StubCertificateDirectory, StubProduct, StubBackend, StubFacts
from subscription_manager.gui.mysubstab import MySubscriptionsTab, WARNING_IMG, EXPIRED_IMG


class MySubscriptionsTabTest(unittest.TestCase):

    def setUp(self):
        self.uep = StubUEP
        self.backend = StubBackend()
        self.consumer = Mock()
        self.facts = StubFacts({})

        self.cert1 = StubEntitlementCertificate(
            StubProduct('product2'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2060, 1, 1),
            quantity="10", stacking_id=None)

        self.cert_dir = StubCertificateDirectory([self.cert1])
        self.my_subs_tab = MySubscriptionsTab(self.backend, self.consumer,
                self.facts, None, self.cert_dir)

    def tearDown(self):
        pass

    def test_image_rank_both_none(self):
        self.assertFalse(self.my_subs_tab.image_ranks_higher(None, None))

    def test_image_rank_new_image_none(self):
        self.assertFalse(self.my_subs_tab.image_ranks_higher(WARNING_IMG, None))

    def test_image_rank_new_image_lower(self):
        self.assertFalse(self.my_subs_tab.image_ranks_higher(EXPIRED_IMG, WARNING_IMG))

    def test_image_rank_new_image_higher(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(WARNING_IMG, EXPIRED_IMG))

    def test_image_rank_old_image_none(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(None, EXPIRED_IMG))

    def test_correct_cert_data_inserted_into_store(self):
        self.cert1.order.stacking_id = None
        column_entries = self._get_entries_for_test()

        self.assertEquals(1, len(column_entries))

        entry = column_entries[0]

        self._assert_entry(entry)

    def test_stacking_entry_inserted_when_stacking_id_exists(self):
        self.cert1.order.stacking_id = 1234
        column_entries = self._get_entries_for_test()

        self.assertEquals(2, len(column_entries))

        self._assert_group_entry(column_entries[0])
        self._assert_entry(column_entries[1])

    def _get_entries_for_test(self):
        column_entries = []

        def collect_entries(iter, entry):
            column_entries.append(entry)

        # Test that the data from a subscription is loaded into the store.
        self.my_subs_tab.store.add_map = collect_entries
        self.my_subs_tab.update_subscriptions()
        return column_entries

    def _assert_entry(self, entry):
        self.assertEquals(self.cert1.getOrder().getName(), entry['subscription'])
        self.assertEquals(self.cert1.validRange().begin(), entry['start_date'])
        self.assertEquals(self.cert1.validRange().end(), entry['expiration_date'])
        self.assertEquals("0 / 1", entry['installed_text'])
        self.assertEquals(0, entry['installed_value'])
        self.assertEquals(self.cert1.getOrder().getQuantityUsed(), entry['quantity'])
        self.assertEquals(self.cert1.serialNumber(), entry['serial'])
        self.assertFalse(entry['is_group_row'])

    def _assert_group_entry(self, entry):
        self.assertEquals(self.cert1.getProduct().getName(),
                          entry['subscription'])
        self.assertFalse('start_date' in entry)
        self.assertFalse('expiration_date' in entry)
        self.assertFalse('installed_text' in entry)
        self.assertEquals(0.0, entry['installed_value'])
        self.assertFalse('quantity' in entry)
        self.assertFalse('serial' in entry)
        self.assertTrue(entry['is_group_row'])
