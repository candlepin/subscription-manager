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
    StubCertificateDirectory, StubFacts
from subscription_manager.certlib import find_first_invalid_date
from subscription_manager.cert_sorter import CertSorter

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
                product_dir=prod_dir)
        self.assertIsNone(last_valid_date)

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
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir, product_dir=product_dir)
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
                product_dir=product_dir)
        self.assertEqual(2050, last_valid_date.year)

    # Checking scenario when we have an entitlement to cover us now, and another
    # for when the first expires:
    def test_future_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product1'),
                start_date=datetime(2049, 1, 1),
                end_date=datetime(2070, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        last_valid_date = find_first_invalid_date(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(2070, last_valid_date.year)
        self.assertEqual(1, last_valid_date.month)
        self.assertEqual(2, last_valid_date.day)

    def test_all_expired_entitlements(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2000, 1, 1),
                end_date=datetime(2001, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product1'),
                start_date=datetime(2000, 12, 1),
                end_date=datetime(2005, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because all entitlements have expired, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(today.year, last_valid_date.year)
        self.assertEqual(today.month, last_valid_date.month)
        self.assertEqual(today.day, last_valid_date.day)


class CertSorterTests(unittest.TestCase):

    def setUp(self):
        # Setup mock product and entitlement certs:
        self.stackable_product1 = StubProduct('stackable_product1',
                                              attributes={'stacking_id': 13,
                                                          'multi-entitlement': 'yes',
                                                          'sockets': 1})
        self.stackable_product2 = StubProduct('stackable_product2',
                                              attributes={'stacking_id': 13,
                                                          'multi-entitlement': 'yes',
                                                          'sockets': 1})

        self.prod_dir = StubCertificateDirectory([
            # Will be unentitled:
            StubProductCertificate(StubProduct('product1')),
            # Will be entitled:
            StubProductCertificate(StubProduct('product2')),
            # Will be entitled but expired:
            StubProductCertificate(StubProduct('product3')),
            StubProductCertificate(self.stackable_product1),
            StubProductCertificate(self.stackable_product2),
        ])

        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('product2')),
            StubEntitlementCertificate(StubProduct('product3'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2)),
            StubEntitlementCertificate(StubProduct('product4'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() + timedelta(days=365),
                order_end_date=datetime.now() - timedelta(days=2)),  # in warning period
            StubEntitlementCertificate(StubProduct('mktproduct',
                                                   attributes={'stacking_id': 13,
                                                               'multi-entitlement': 'yes',
                                                               'sockets': 1})),
            StubEntitlementCertificate(self.stackable_product1),
            StubEntitlementCertificate(self.stackable_product2),
            ])

    def test_unentitled_product_certs(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEqual(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue('product1' in self.sorter.unentitled_products)

    # def test_entitled_products(self):
    #     self.sorter = CertSorter(self.prod_dir, self.ent_dir)
    #     self.assertEqual(2, len(self.sorter.valid_products.keys()))
    #     self.assertTrue('product2' in self.sorter.valid_products)
    #     self.assertTrue('product4' in self.sorter.valid_products)

    #     self.assertEqual(2, len(self.sorter.valid_entitlement_certs))
    #     self.assertTrue(cert_list_has_product(
    #         self.sorter.valid_entitlement_certs, 'product2'))
    #     self.assertTrue(cert_list_has_product(
    #         self.sorter.valid_entitlement_certs, 'product4'))

    def test_expired(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEqual(2, len(self.sorter.expired_entitlement_certs))

        self.assertTrue(cert_list_has_product(
            self.sorter.expired_entitlement_certs, 'product3'))
        # Certificate in warning period should show up as expired, even though
        # they can technically still be used. We use the CertSorter to warn
        # customer of invalid entitlement issues.
        self.assertTrue(cert_list_has_product(
            self.sorter.expired_entitlement_certs, 'product4'))

        self.assertEqual(1, len(self.sorter.expired_products.keys()))
        self.assertTrue('product3' in self.sorter.expired_products)

    def test_expired_in_future(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                on_date=datetime(2050, 1, 1))
        self.assertEqual(6, len(self.sorter.expired_entitlement_certs))
        self.assertTrue('product2' in self.sorter.expired_products)
        self.assertTrue('product3' in self.sorter.expired_products)
        self.assertFalse('product4' in self.sorter.expired_products)  # it's not installed
        self.assertTrue('product1' in self.sorter.unentitled_products)
        self.assertEqual(0, len(self.sorter.valid_entitlement_certs))

    def test_entitled_products(self):
        provided = [StubProduct('product1'), StubProduct('product2'),
                StubProduct('product3')]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('mktproduct'),
                provided_products=provided)])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEquals(3, len(self.sorter.valid_products.keys()))
        self.assertTrue('product1' not in self.sorter.partially_valid_products)
        self.assertTrue('product1' in self.sorter.valid_products)
        self.assertTrue('product2' in self.sorter.valid_products)
        self.assertTrue('product3' in self.sorter.valid_products)

    def test_expired_but_provided_in_another_entitlement(self):
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('mktproduct'),
                provided_products=[StubProduct('product3')]),
            StubEntitlementCertificate(StubProduct('mktproduct'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2),
                provided_products=[StubProduct('product3')]),
            StubEntitlementCertificate(StubProduct('product4'))
        ])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEquals(1, len(self.sorter.valid_products.keys()))
        self.assertTrue('product3' in self.sorter.valid_products)
        self.assertEquals(0, len(self.sorter.expired_products.keys()))
        self.assertEquals(4, len(self.sorter.unentitled_products.keys()))

    def test_multi_product_entitlement_expired(self):
        # Setup one ent cert that provides everything we have installed (see setUp)
        provided = [StubProduct('product2'), StubProduct('product3'),
                    self.stackable_product1, self.stackable_product2]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('mktproduct'),
                provided_products=provided)])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                on_date=datetime(2050, 1, 1))

        self.assertEquals(1, len(self.sorter.expired_entitlement_certs))
        self.assertEquals(4, len(self.sorter.expired_products.keys()))
        self.assertTrue('product2' in self.sorter.expired_products)
        self.assertTrue('product3' in self.sorter.expired_products)

        self.assertEquals(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue('product1' in self.sorter.unentitled_products)


    def test_stacking_product(self):
        provided = [self.stackable_product1, self.stackable_product2]
        self.ent_dir = StubCertificateDirectory([
                StubEntitlementCertificate(StubProduct('mktproduct',
                                                       attributes={'stacking_id': 13,
                                                                   'multi-entitlement': 'yes',
                                                                   'sockets': 1}),
                                           provided_products=provided)])
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 1})
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, facts_dict=stub_facts.get_facts())
        self.assertFalse('stackable_product1' in self.sorter.unentitled_products)

    def test_stacking_product_1_socket(self):
        provided = [self.stackable_product1]
        self.ent_dir = StubCertificateDirectory([
                StubEntitlementCertificate(StubProduct('mktproduct',
                                                       attributes={}),
                                           provided_products=provided)])
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 1})
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, facts_dict=stub_facts.get_facts())

        self.assertFalse('stackable_product1' in self.sorter.unentitled_products)

    # product with more sockets than we need (valid)
    # product without enouch sockets (partail)
    # product with no sockets

    def test_stacking_product_needs_more_sockets(self):
        provided = [self.stackable_product1]
        mkt_product = StubProduct('mktproduct',
                                 attributes={'stacking_id': 13,
                                             'multi-entitlement': 'yes',
                                             'sockets': 1})
        mkt_product_cert = StubProductCertificate(mkt_product)
        self.prod_dir.certs.append(mkt_product_cert)
        self.ent_dir = StubCertificateDirectory([
                StubEntitlementCertificate(mkt_product, provided_products=provided,
                                           quantity=2)])
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 42})
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, facts_dict=stub_facts.get_facts())
        # we are partially valid
        self.assertTrue('mktproduct' in self.sorter.partially_valid_products)
        # but we are also entitled enough to get content
        self.assertTrue('mktproduct' in self.sorter.unentitled_products)

    def test_stacking_product_two_pools_needed(self):
        provided = [self.stackable_product1, self.stackable_product2]
        mkt_product = StubProduct('mktproduct',
                                 attributes={'stacking_id': 13,
                                             'multi-entitlement': 'yes',
                                             'sockets': 1})
        mkt_product_cert = StubProductCertificate(mkt_product)
        self.prod_dir.certs.append(mkt_product_cert)
        self.ent_dir = StubCertificateDirectory([
                StubEntitlementCertificate(mkt_product, provided_products=provided)])
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 2})
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, facts_dict=stub_facts.get_facts())
        self.assertFalse('stackable_product1' in self.sorter.unentitled_products)
        self.assertFalse('stackable_product2' in self.sorter.unentitled_products)


def cert_list_has_product(cert_list, product_id):
    for cert in cert_list:
        for product in cert.getProducts():
            if product.getHash() == product_id:
                return True
    return False
