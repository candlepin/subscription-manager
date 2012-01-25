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
    CertSorter, FUTURE_SUBSCRIBED, SUBSCRIBED, NOT_SUBSCRIBED, EXPIRED, PARTIALLY_SUBSCRIBED
from datetime import timedelta, datetime
from rhsm.certificate import GMT


def cert_list_has_product(cert_list, product_id):
    for cert in cert_list:
        for product in cert.getProducts():
            if product.getHash() == product_id:
                return True
    return False


INST_PID_1 = 1001
INST_PID_2 = 1002
INST_PID_3 = 1003
INST_PID_4 = 1004
INST_PID_5 = 1005
INST_PID_6 = 1006
STACK_1 = 'stack1'
STACK_2 = 'stack2'


class CertSorterTests(unittest.TestCase):

    def setUp(self):
        # Setup mock product and entitlement certs:
        self.prod_dir = StubCertificateDirectory([
            # Will be unentitled:
            StubProductCertificate(StubProduct(INST_PID_1)),
            # Will be entitled:
            StubProductCertificate(StubProduct(INST_PID_2)),
            # Will be entitled but expired:
            StubProductCertificate(StubProduct(INST_PID_3)),
        ])

        self.ent_dir = StubEntitlementDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_2)),
            StubEntitlementCertificate(StubProduct(INST_PID_3),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2)),
            StubEntitlementCertificate(StubProduct(INST_PID_4),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() + timedelta(days=365)),
            StubEntitlementCertificate(StubProduct(INST_PID_5)),
            # entitled, but not installed
            StubEntitlementCertificate(StubProduct('not_installed_product')),
            ])

    def test_unentitled_product_certs(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})
        self.assertEqual(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue(INST_PID_1 in self.sorter.unentitled_products)
        self.assertFalse(self.sorter.is_valid())
        self.assertEqual(NOT_SUBSCRIBED, self.sorter.get_status(INST_PID_1))

    def test_ent_cert_no_installed_product(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})
        # TODO: looks like this test was never completed

    def test_ent_cert_no_product(self):
        self.ent_dir = StubCertificateDirectory(
            [StubEntitlementCertificate(None, provided_products=[],
                                        quantity=2)])

        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 42})
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                stub_facts.get_facts())

        self.assertEqual(0, len(self.sorter.partially_valid_products))

    def test_expired(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})
        self.assertEqual(1, len(self.sorter.expired_entitlement_certs))

        self.assertTrue(cert_list_has_product(
            self.sorter.expired_entitlement_certs, INST_PID_3))

        self.assertEqual(1, len(self.sorter.expired_products.keys()))
        self.assertTrue(INST_PID_3 in self.sorter.expired_products)
        self.assertFalse(self.sorter.is_valid())
        self.assertEquals(EXPIRED, self.sorter.get_status(INST_PID_3))

    def test_expired_in_future(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {},
                on_date=datetime(2050, 1, 1,tzinfo=GMT()))
        self.assertEqual(5, len(self.sorter.expired_entitlement_certs))
        self.assertTrue(INST_PID_2 in self.sorter.expired_products)
        self.assertTrue(INST_PID_3 in self.sorter.expired_products)
        self.assertFalse(INST_PID_4 in self.sorter.expired_products)  # it's not installed
        self.assertTrue(INST_PID_1 in self.sorter.unentitled_products)
        self.assertEqual(0, len(self.sorter.valid_entitlement_certs))
        self.assertFalse(self.sorter.is_valid())

    def test_entitled_products(self):
        provided = [StubProduct(INST_PID_1), StubProduct(INST_PID_2),
                StubProduct(INST_PID_3)]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                provided_products=provided)])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})
        self.assertEquals(3, len(self.sorter.valid_products.keys()))
        self.assertTrue(INST_PID_1 not in self.sorter.partially_valid_products)
        self.assertTrue(INST_PID_1 in self.sorter.valid_products)
        self.assertTrue(INST_PID_2 in self.sorter.valid_products)
        self.assertTrue(INST_PID_3 in self.sorter.valid_products)
        self.assertTrue(self.sorter.is_valid())

    def test_expired_but_provided_in_another_entitlement(self):
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                provided_products=[StubProduct(INST_PID_3)]),
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2),
                provided_products=[StubProduct(INST_PID_3)]),
            StubEntitlementCertificate(StubProduct(INST_PID_4))
        ])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})
        self.assertEquals(1, len(self.sorter.valid_products.keys()))
        self.assertTrue(INST_PID_3 in self.sorter.valid_products)
        self.assertEquals(0, len(self.sorter.expired_products.keys()))

    def test_multi_product_entitlement_expired(self):
        # Setup one ent cert that provides several things installed
        # installed:
        provided = [StubProduct(INST_PID_2), StubProduct(INST_PID_3)]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                provided_products=provided)])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {},
                on_date=datetime(2050, 1, 1, tzinfo=GMT()))

        self.assertEquals(1, len(self.sorter.expired_entitlement_certs))
        self.assertEquals(2, len(self.sorter.expired_products.keys()))
        self.assertTrue(INST_PID_2 in self.sorter.expired_products)
        self.assertTrue(INST_PID_3 in self.sorter.expired_products)

        # Expired should not show up as unentitled also:
        self.assertEquals(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue(INST_PID_1 in self.sorter.unentitled_products)
        self.assertFalse(self.sorter.is_valid())

    def test_future_entitled(self):
        provided = [StubProduct(INST_PID_2), StubProduct(INST_PID_3)]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                provided_products=provided,
                start_date=datetime.now() + timedelta(days=30),
                end_date=datetime.now() + timedelta(days=120)),
            ])

        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})

        self.assertEquals(0, len(self.sorter.valid_products))
        self.assertEquals(2, len(self.sorter.future_products))
        self.assertEquals(3, len(self.sorter.unentitled_products))
        self.assertTrue(INST_PID_2 in self.sorter.future_products)
        self.assertTrue(INST_PID_3 in self.sorter.future_products)
        self.assertEquals(FUTURE_SUBSCRIBED, self.sorter.get_status(INST_PID_2))
        self.assertEquals(FUTURE_SUBSCRIBED, self.sorter.get_status(INST_PID_3))

    def test_future_and_currently_entitled(self):
        provided = [StubProduct(INST_PID_2), StubProduct(INST_PID_3)]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                provided_products=provided,
                start_date=datetime.now() + timedelta(days=30),
                end_date=datetime.now() + timedelta(days=120)),
            StubEntitlementCertificate(StubProduct(INST_PID_5),
                provided_products=provided),
            ])

        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {})

        self.assertEquals(2, len(self.sorter.valid_products))
        self.assertEquals(2, len(self.sorter.future_products))
        self.assertEquals(1, len(self.sorter.unentitled_products))
        self.assertTrue(INST_PID_2 in self.sorter.future_products)
        self.assertTrue(INST_PID_3 in self.sorter.future_products)
        self.assertTrue(INST_PID_2 in self.sorter.valid_products)
        self.assertTrue(INST_PID_3 in self.sorter.valid_products)
        self.assertEquals(SUBSCRIBED, self.sorter.get_status(INST_PID_2))
        self.assertEquals(SUBSCRIBED, self.sorter.get_status(INST_PID_3))


class CertSorterStackingTests(unittest.TestCase):

    def stub_prod_cert(self, pid):
        return StubProductCertificate(StubProduct(INST_PID_1))

    def test_simple_partial_stack(self):
        prod_dir = StubCertificateDirectory([self.stub_prod_cert(INST_PID_1)])
        # System has 8 sockets:
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
        # Only 2 sockets covered:
        ent_dir = StubCertificateDirectory([
            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=2)])
        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts())

        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
        self.assertFalse(INST_PID_1 in sorter.valid_products)
        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
        self.assertEquals(1, len(sorter.partially_valid_products))
        self.assertEquals(1, len(sorter.partially_valid_products[INST_PID_1]))

    def test_simple_full_stack_multicert(self):
        prod_dir = StubCertificateDirectory([self.stub_prod_cert(INST_PID_1)])
        # System has 8 sockets:
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
        # 2 ent certs providing 4 sockets each means we're valid:
        ent_dir = StubCertificateDirectory([
            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=4),
            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=4)])
        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts())

        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
        self.assertTrue(INST_PID_1 in sorter.valid_products)
        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
        self.assertEquals(0, len(sorter.partially_valid_products))

    def test_simple_full_stack_singlecert_with_quantity(self):
        prod_dir = StubCertificateDirectory([self.stub_prod_cert(INST_PID_1)])
        # System has 8 sockets:
        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
        # 1 ent cert providing 4 sockets with quantity 2 means we're valid:
        ent_dir = StubCertificateDirectory([
            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1,
                sockets=4, quantity=2)])
        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts())

        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
        self.assertTrue(INST_PID_1 in sorter.valid_products)
        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
        self.assertEquals(0, len(sorter.partially_valid_products))

    # This is still technically invalid:
    def test_partial_stack_for_uninstalled_products(self):
        # No products installed:
        prod_dir = StubCertificateDirectory([])

        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 42})
        ents = []
        ents.append(stub_ent_cert(INST_PID_5, ['prod1'],
            stack_id=STACK_1, quantity=2))
        ent_dir = StubCertificateDirectory(ents)
        sorter = CertSorter(prod_dir, ent_dir,
                stub_facts.get_facts())

        # No installed products, so nothing should show up as partially valid:
        self.assertEquals(0, len(sorter.partially_valid_products))

        self.assertEquals(1, len(sorter.partial_stacks))
        self.assertTrue(STACK_1 in sorter.partial_stacks)
        self.assertFalse(sorter.is_valid())

    # Entitlements with the same stack ID will not necessarily have the same
    # first product, thus why we key off stacking_id attribute:
    def test_partial_stack_different_first_product(self):
        prod_dir = StubCertificateDirectory([self.stub_prod_cert(INST_PID_1)])

        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 4})
        ents = []
        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
            stack_id=STACK_1, sockets=1))
        ents.append(stub_ent_cert(INST_PID_6, [INST_PID_1],
            stack_id=STACK_1, sockets=1))
        ent_dir = StubCertificateDirectory(ents)

        sorter = CertSorter(prod_dir, ent_dir,
                stub_facts.get_facts())

        # Installed product should show up as partially valid:
        self.assertEquals(1, len(sorter.partially_valid_products))
        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
        self.assertFalse(INST_PID_1 in sorter.valid_products)
        self.assertTrue(STACK_1 in sorter.partial_stacks)

    # Edge case, but technically two stacks could have same first product
    def test_multiple_partial_stacks_same_first_product(self):
        prod_dir = StubCertificateDirectory([
            self.stub_prod_cert(INST_PID_1)])

        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 4})

        ents = []
        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
            stack_id=STACK_1, sockets=1))
        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
            stack_id=STACK_2, sockets=1))
        ent_dir = StubCertificateDirectory(ents)
        sorter = CertSorter(prod_dir, ent_dir,
                stub_facts.get_facts())

        # Our installed product should be partially valid:
        self.assertEquals(1, len(sorter.partially_valid_products))
        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
        self.assertFalse(INST_PID_1 in sorter.valid_products)
        self.assertEquals(2, len(sorter.partial_stacks))
        self.assertTrue(STACK_1 in sorter.partial_stacks)
        self.assertTrue(STACK_2 in sorter.partial_stacks)

    def test_valid_stack_different_first_products(self):
        prod_dir = StubCertificateDirectory([self.stub_prod_cert(INST_PID_1)])

        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 4})
        # Two entitlements, same stack, different first products, each
        # providing 2 sockets: (should be valid)
        ents = []
        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
            stack_id=STACK_1, sockets=2))
        ents.append(stub_ent_cert(INST_PID_6, [INST_PID_1],
            stack_id=STACK_1, sockets=2))
        ent_dir = StubCertificateDirectory(ents)

        sorter = CertSorter(prod_dir, ent_dir,
                stub_facts.get_facts())

        # Installed product should show up as valid:
        self.assertEquals(1, len(sorter.valid_products))
        self.assertTrue(INST_PID_1 in sorter.valid_products)
        self.assertEquals(0, len(sorter.partially_valid_products))
        self.assertEquals(0, len(sorter.partial_stacks))


class TestCertSorterStatus(unittest.TestCase):

    def test_subscribed(self):
        product = create_prod_cert(INST_PID_1)
        entitlement = stub_ent_cert(INST_PID_1)
        sorter = create_cert_sorter([product], [entitlement])
        self.assertEqual(SUBSCRIBED, sorter.get_status(INST_PID_1))

    def test_not_subscribed(self):
        installed = create_prod_cert(INST_PID_1);
        sorter = create_cert_sorter([installed], [])
        self.assertEqual(NOT_SUBSCRIBED, sorter.get_status(INST_PID_1))

    def test_expired(self):
        installed = create_prod_cert(INST_PID_1);
        expired_ent = stub_ent_cert(INST_PID_1,
                                         start_date=datetime.now() - timedelta(days=365),
                                         end_date=datetime.now() - timedelta(days=2))
        sorter = create_cert_sorter([installed], [expired_ent])
        self.assertEqual(EXPIRED, sorter.get_status(INST_PID_1))

    def test_future_subscribed(self):
        installed = create_prod_cert(INST_PID_1);
        expired_ent = stub_ent_cert(INST_PID_1,
                                         start_date=datetime.now() + timedelta(days=10),
                                         end_date=datetime.now() + timedelta(days=365))
        sorter = create_cert_sorter([installed], [expired_ent])
        self.assertEqual(FUTURE_SUBSCRIBED, sorter.get_status(INST_PID_1))

    def test_partially_subscribed(self):
        installed = create_prod_cert(INST_PID_1);
        partial_ent = stub_ent_cert(INST_PID_2, [INST_PID_1], quantity=1,
                                         stack_id=STACK_1, sockets=2)
        sorter = create_cert_sorter([installed], [partial_ent])
        self.assertEqual(PARTIALLY_SUBSCRIBED, sorter.get_status(INST_PID_1))

    def test_partially_subscribed_and_future_subscription(self):
        installed = create_prod_cert(INST_PID_1);
        partial_ent = stub_ent_cert(INST_PID_2, [INST_PID_1], quantity=1,
                                         stack_id=STACK_1, sockets=2)
        future_ent = stub_ent_cert(INST_PID_2, [INST_PID_1], quantity=1,
                                         stack_id=STACK_1, sockets=2,
                                         start_date=datetime.now() + timedelta(days=10),
                                         end_date=datetime.now() + timedelta(days=365))
        sorter = create_cert_sorter([installed], [partial_ent, future_ent])
        self.assertEqual(PARTIALLY_SUBSCRIBED, sorter.get_status(INST_PID_1))

    def test_expired_and_future_entitlements_report_future(self):
        installed = create_prod_cert(INST_PID_1);
        expired_ent = stub_ent_cert(INST_PID_1,
                                         start_date=datetime.now() - timedelta(days=365),
                                         end_date=datetime.now() - timedelta(days=10))
        future_ent = stub_ent_cert(INST_PID_1,
                                         start_date=datetime.now() + timedelta(days=10),
                                         end_date=datetime.now() + timedelta(days=365))

        sorter = create_cert_sorter([installed], [future_ent, expired_ent])
        self.assertEqual(FUTURE_SUBSCRIBED, sorter.get_status(INST_PID_1))


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


def stub_ent_cert(parent_pid, provided_pids=[], quantity=1,
        stack_id=None, sockets=1, start_date=None, end_date=None):
    provided_prods = []
    for provided_pid in provided_pids:
        provided_prods.append(StubProduct(provided_pid))

    parent_prod = StubProduct(parent_pid)

    return StubEntitlementCertificate(parent_prod,
            provided_products=provided_prods, quantity=quantity,
            stacking_id=stack_id, sockets=sockets, start_date=start_date,
            end_date=end_date)

def create_prod_cert(pid):
    return StubProductCertificate(StubProduct(pid))

def create_cert_sorter(product_certs, entitlement_certs, machine_sockets=8):
    stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": machine_sockets})
    return CertSorter(StubCertificateDirectory(product_certs),
                      StubEntitlementDirectory(entitlement_certs),
                      stub_facts.get_facts())