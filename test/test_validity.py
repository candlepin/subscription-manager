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
from datetime import timedelta, datetime

from stubs import StubEntitlementCertificate, StubProduct, StubProductCertificate, \
    StubCertificateDirectory
from subscription_manager.validity import find_first_invalid_date

from rhsm.certificate import GMT

class FindFirstInvalidDateTests(unittest.TestCase):

    # No product certs installed, but we manually got entitlements:
    def test_just_entitlements(self):
        cert1 = StubEntitlementCertificate(
                    StubProduct('product1'), start_date=datetime(2010, 1, 1),
                    end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                    StubProduct('product2'),
                    start_date=datetime(2010, 1, 1),
                    end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])
        prod_dir = StubCertificateDirectory([])

        last_valid_date = find_first_invalid_date(ent_dir=ent_dir,
                product_dir=prod_dir, facts_dict={})
        self.assertTrue(last_valid_date is None)

    def test_currently_unentitled_products(self):
        cert = StubProductCertificate(StubProduct('unentitledProduct'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because we have an unentitled product, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir,
                product_dir=product_dir, facts_dict={})
        self.assertEqual(today.year, last_valid_date.year)
        self.assertEqual(today.month, last_valid_date.month)
        self.assertEqual(today.day, last_valid_date.day)

    def test_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        last_valid_date = find_first_invalid_date(ent_dir=ent_dir,
                product_dir=product_dir, facts_dict={})
        self.assertEqual(2050, last_valid_date.year)

    # Checking scenario when we have an entitlement to cover us now, and another
    # for when the first expires:
    def test_future_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1, tzinfo=GMT()),
                end_date=datetime(2050, 1, 1, tzinfo=GMT()))
        cert2 = StubEntitlementCertificate(
                StubProduct('product1'),
                start_date=datetime(2049, 1, 1, tzinfo=GMT()),
                end_date=datetime(2070, 1, 1, tzinfo=GMT()))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        last_valid_date = find_first_invalid_date(ent_dir=ent_dir,
                product_dir=product_dir, facts_dict={})
        self.assertEqual(2070, last_valid_date.year)
        self.assertEqual(1, last_valid_date.month)
        self.assertEqual(2, last_valid_date.day)

    def test_all_expired_entitlements(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2000, 1, 1, tzinfo=GMT()),
                end_date=datetime(2001, 1, 1, tzinfo=GMT()))
        cert2 = StubEntitlementCertificate(
                StubProduct('product1'),
                start_date=datetime(2000, 12, 1,tzinfo=GMT()),
                end_date=datetime(2005, 1, 1, tzinfo=GMT()))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because all entitlements have expired, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir,
                product_dir=product_dir, facts_dict={})
        self.assertEqual(today.year, last_valid_date.year)
        self.assertEqual(today.month, last_valid_date.month)
        self.assertEqual(today.day, last_valid_date.day)
