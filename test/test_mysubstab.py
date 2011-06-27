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
from stubs import StubUEP, StubEntitlementCertificate, StubCertificateDirectory, StubProduct, StubBackend
from subscription_manager.gui.mysubstab import MySubscriptionsTab

class MySubscriptionsTabTest(unittest.TestCase):

    def setUp(self):
        self.uep = StubUEP
        self.backend = StubBackend()
        self.consumer = Mock()
        self.consumer.uuid = "1234"
        self.consumer.name = "Test Consumer"

        self.cert1 = StubEntitlementCertificate(
            StubProduct('product2'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2060, 1, 1),
            quantity="10")

        self.cert_dir = StubCertificateDirectory([self.cert1]);


    def tearDown(self):
        pass

    def test_correct_cert_data_inserted_into_store(self):
        column_entries = []

        def collect_entries(entry):
            column_entries.append(entry);

        # Test that the data from a subscription is loaded into the store.
        my_subs_tab = MySubscriptionsTab(self.backend, self.consumer, {}, self.cert_dir)
        my_subs_tab.store.add_map = collect_entries
        my_subs_tab.update_subscriptions();

        self.assertEquals(1, len(column_entries))

        column = column_entries[0]

        self.assertEquals(self.cert1.getOrder().getName(), column['subscription'])
        self.assertEquals(self.cert1.validRange().begin(), column['start_date'])
        self.assertEquals(self.cert1.validRange().end(), column['expiration_date'])
        self.assertEquals("0 / 1", column['installed_text'])
        self.assertEquals(0, column['installed_value'])
        self.assertEquals(self.cert1.getOrder().getQuantity(), column['quantity'])
        self.assertEquals(self.cert1.serialNumber(), column['serial']);
