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

import datetime

from fixture import SubManFixture
from stubs import StubUEP, StubEntitlementCertificate, \
        StubCertificateDirectory, StubProduct, StubBackend, \
        StubProductDirectory
from subscription_manager.gui.mysubstab import MySubscriptionsTab, \
        EXPIRING_IMG, WARNING_IMG, EXPIRED_IMG
from mock import Mock


class MySubscriptionsTabTest(SubManFixture):

    def setUp(self):
        super(MySubscriptionsTabTest, self).setUp()
        self.uep = StubUEP
        self.backend = StubBackend()

        self.cert1 = StubEntitlementCertificate(
            StubProduct('product2'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2060, 1, 1),
            quantity="10", ent_id='prod2')
        self.cert2 = StubEntitlementCertificate(
            StubProduct('product3'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2060, 1, 1),
            quantity="10", ent_id='prod3')

        self.cert_dir = StubCertificateDirectory([self.cert1, self.cert2])
        self.my_subs_tab = MySubscriptionsTab(self.backend,
                                              None,
                                              self.cert_dir,
                                              StubProductDirectory([]))

    def tearDown(self):
        pass

    def test_get_entry_image_expired(self):
        cert = StubEntitlementCertificate(
                    StubProduct('product2'),
                    start_date=datetime.datetime(2010, 1, 1),
                    end_date=datetime.datetime(2011, 1, 1),
                    quantity="10", stacking_id=None)
        image = self.my_subs_tab._get_entry_image(cert)
        self.assertEqual(EXPIRED_IMG, image)

    def test_get_entry_image_expiring(self):
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        cert = StubEntitlementCertificate(
                    StubProduct('product2'),
                    start_date=datetime.datetime(2010, 1, 1),
                    end_date=tomorrow,
                    quantity="10", stacking_id=None)
        image = self.my_subs_tab._get_entry_image(cert)
        self.assertEqual(EXPIRING_IMG, image)

    def test_get_entry_image_warning(self):
        ending = datetime.datetime.now() + datetime.timedelta(days=300)
        cert = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime.datetime(2010, 1, 1),
                end_date=ending,
                quantity="10", ent_id='ent')
        self.my_subs_tab.backend.cs.reasons.get_subscription_reasons = Mock(return_value=['Some detail'])
        image = self.my_subs_tab._get_entry_image(cert)
        self.assertEqual(WARNING_IMG, image)

    def test_image_rank_both_none(self):
        self.assertFalse(self.my_subs_tab.image_ranks_higher(None, None))

    def test_image_rank_new_image_none(self):
        self.assertFalse(self.my_subs_tab.image_ranks_higher(EXPIRING_IMG, None))

    def test_image_rank_new_image_lower(self):
        self.assertFalse(self.my_subs_tab.image_ranks_higher(EXPIRED_IMG, EXPIRING_IMG))

    def test_image_rank_new_image_higher(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(EXPIRING_IMG, EXPIRED_IMG))

    def test_image_rank_old_image_none(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(None, EXPIRED_IMG))

    def test_image_rank_warn_none(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(None, WARNING_IMG))

    def test_image_rank_warn_expiring(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(WARNING_IMG, EXPIRING_IMG))

    def test_image_rank_warn_expired(self):
        self.assertTrue(self.my_subs_tab.image_ranks_higher(WARNING_IMG, EXPIRED_IMG))

    def test_correct_cert_data_inserted_into_store(self):
        self.cert1.order.stacking_id = None
        self.cert2.order.stacking_id = None

        column_entries = self._get_entries_for_test()

        self.assertEquals(2, len(column_entries))

        self._assert_entry_1(column_entries[0])
        self._assert_entry_2(column_entries[1])

    def test_stacking_entry_not_inserted_when_stacking_id_exists(self):
        self.cert1.order.stacking_id = 1234
        self.cert2.order.stacking_id = None
        column_entries = self._get_entries_for_test()

        # single entry with stacking_id: no stacking entry
        self.assertEquals(2, len(column_entries))

        self._assert_entry_1(column_entries[0])
        self._assert_entry_2(column_entries[1])

    def test_stacking_entry_inserted_when_stacking_id_exists(self):
        self.cert1.order.stacking_id = 1234
        self.cert2.order.stacking_id = 1234
        column_entries = self._get_entries_for_test()

        self.assertEquals(3, len(column_entries))

        self._assert_group_entry(column_entries[0])
        self._assert_entry_1(column_entries[1])
        self._assert_entry_2(column_entries[2])

    def test_no_subscriptions_unregister_button_is_blank(self):
        cert_dir = StubCertificateDirectory([])
        my_subs_tab = MySubscriptionsTab(self.backend,
                                         None,
                                         cert_dir,
                                         StubProductDirectory([]))
        self.assertFalse(my_subs_tab.unsubscribe_button.get_property('sensitive'))

    def test_unselect_unregister_button_is_blank(self):
        self.my_subs_tab.on_no_selection()
        self.assertFalse(self.my_subs_tab.unsubscribe_button.get_property('sensitive'))

    def _get_entries_for_test(self):
        column_entries = []

        def collect_entries(tree_iter, entry):
            column_entries.append(entry)

        # Test that the data from a subscription is loaded into the store.
        self.my_subs_tab.store.add_map = collect_entries
        self.my_subs_tab.update_subscriptions()
        return column_entries

    def _assert_entry_1(self, entry):
        self.assertEquals(self.cert1.order.name, entry['subscription'])
        self.assertEquals(self.cert1.valid_range.begin(), entry['start_date'])
        self.assertEquals(self.cert1.valid_range.end(), entry['expiration_date'])
        self.assertEquals("0 / 1", entry['installed_text'])
        self.assertEquals(0, entry['installed_value'])
        # The quantity/serial column is of type string, so when we fetch it from the
        # widget, it is a str.
        self.assertEquals(str(self.cert1.order.quantity_used), entry['quantity'])
        self.assertEquals(str(self.cert1.serial), entry['serial'])
        self.assertFalse(entry['is_group_row'])

    def _assert_entry_2(self, entry):
        self.assertEquals(self.cert2.order.name, entry['subscription'])
        self.assertEquals(self.cert2.valid_range.begin(), entry['start_date'])
        self.assertEquals(self.cert2.valid_range.end(), entry['expiration_date'])
        self.assertEquals("0 / 1", entry['installed_text'])
        self.assertEquals(0, entry['installed_value'])
        self.assertEquals(str(self.cert2.order.quantity_used), entry['quantity'])
        self.assertEquals(str(self.cert2.serial), entry['serial'])
        self.assertFalse(entry['is_group_row'])

    def _assert_group_entry(self, entry):
        self.assertEquals("Stack of %s and 1 other" % self.cert1.order.name,
                          entry['subscription'])
        self.assertFalse('start_date' in entry)
        self.assertFalse('expiration_date' in entry)
        self.assertFalse('installed_text' in entry)
        self.assertEquals(0.0, entry['installed_value'])
        self.assertFalse('quantity' in entry)
        self.assertFalse('serial' in entry)
        self.assertTrue(entry['is_group_row'])
