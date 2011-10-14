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
from stubs import StubEntitlementCertificate, StubProduct, StubProductCertificate, \
    StubCertificateDirectory, StubEntitlementDirectory, StubFacts
from subscription_manager.cert_sorter import EntitlementCertStackingGroupSorter, \
        CertSorter
from datetime import timedelta, datetime
from rhsm.certificate import GMT


def cert_list_has_product(cert_list, product_id):
    for cert in cert_list:
        for product in cert.getProducts():
            if product.getHash() == product_id:
                return True
    return False


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
        self.stackable_product_not_inst =  StubProduct('stackable_product_not_inst',
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

        self.ent_dir = StubEntitlementDirectory([
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
            # entitled, but not installed
            StubEntitlementCertificate(StubProduct('not_installed_product')),
            # entitled, stackable, but not installed
            StubEntitlementCertificate(self.stackable_product_not_inst),
            ])

    def test_unentitled_product_certs(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEqual(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue('product1' in self.sorter.unentitled_products)

    def test_ent_cert_no_installed_product(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        print self.prod_dir.list()

    def test_ent_cert_no_product(self):
        self.ent_dir = StubCertificateDirectory(
            [StubEntitlementCertificate(None, provided_products=[],
                                        quantity=2)])

        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 42})
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                                 facts_dict=stub_facts.get_facts())

        self.assertEqual(0, len(self.sorter.partially_valid_products))


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
                on_date=datetime(2050, 1, 1,tzinfo=GMT()))
        self.assertEqual(8, len(self.sorter.expired_entitlement_certs))
        self.assertTrue('product2' in self.sorter.expired_products)
        self.assertTrue('product3' in self.sorter.expired_products)
        self.assertFalse('product4' in self.sorter.expired_products)  # it's not installed
        self.assertTrue('product1' in self.sorter.unentitled_products)
        self.assertEqual(0, len(self.sorter.valid_entitlement_certs))
        self.assertFalse(self.sorter.is_valid())

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
                on_date=datetime(2050, 1, 1, tzinfo=GMT()))

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
    # entitled product, no product cert


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

        # partially entitled is not entitled, so we shouldn't be in both
        self.assertTrue('mktproduct' not in self.sorter.valid_products)

        # and also, we shouldn't be in unentitled_products
        self.assertTrue('mktproduct' not in self.sorter.unentitled_products)

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


class TestEntitlementCertStackingGroupSorter(unittest.TestCase):

    def test_sorter_adds_group_for_non_stackable_entitlement(self):
        ent1_prod = StubProduct("Product 1")
        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=None)
        entitlements = [ent1]

        sorter = EntitlementCertStackingGroupSorter(entitlements)
        # With no stacking id, we expect an empty group name
        self._assert_1_group_with_1_entitlement("", ent1, sorter)

    def test_sorter_adds_group_for_stackable_entitlement(self):
        ent1_prod = StubProduct("Product 1")
        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=3)
        entitlements = [ent1]

        sorter = EntitlementCertStackingGroupSorter(entitlements)
        self._assert_1_group_with_1_entitlement('Product 1', ent1, sorter)

    def test_sorter_adds_multiple_entitlements_to_group_when_same_stacking_id(self):
        expected_stacking_id = 5

        ent1_prod = StubProduct("Product 1")
        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=expected_stacking_id)

        ent2_prod = StubProduct("Product 2")
        ent2 = StubEntitlementCertificate(ent2_prod, stacking_id=expected_stacking_id)
        entitlements = [ent1, ent2]

        sorter = EntitlementCertStackingGroupSorter(entitlements)
        self.assertEquals(1, len(sorter.groups))
        self.assertEquals("Product 1", sorter.groups[0].name)
        self.assertEquals(2, len(sorter.groups[0].entitlements))
        self.assertEquals(ent1, sorter.groups[0].entitlements[0])
        self.assertEquals(ent2, sorter.groups[0].entitlements[1])

    def test_sorter_adds_multiple_groups_for_non_stacking_entitlements(self):
        ent1_prod = StubProduct("Product 1")
        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=None)

        ent2_prod = StubProduct("Product 2")
        ent2 = StubEntitlementCertificate(ent2_prod, stacking_id=None)

        entitlements = [ent1, ent2]

        sorter = EntitlementCertStackingGroupSorter(entitlements)
        self.assertEquals(2, len(sorter.groups))

        self.assertEquals('', sorter.groups[0].name)
        self.assertEquals(1, len(sorter.groups[0].entitlements))
        self.assertEquals(ent1, sorter.groups[0].entitlements[0])

        self.assertEquals('', sorter.groups[1].name)
        self.assertEquals(1, len(sorter.groups[1].entitlements))
        self.assertEquals(ent2, sorter.groups[1].entitlements[0])

    def _assert_1_group_with_1_entitlement(self, name, entitlement, sorter):
        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEquals(name, group.name)
        self.assertEquals(1, len(group.entitlements))
        self.assertEquals(entitlement, group.entitlements[0])
