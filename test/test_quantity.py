#
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
from stubs import StubFacts, StubEntitlementCertificate, StubProduct
from modelhelpers import create_pool
from subscription_manager.quantity import QuantityDefaultValueCalculator

class TestQuantityDefaultValueCalculator(unittest.TestCase):

    product_id_1 = "test-product-1"
    product_id_2 = "test-product-2"

    entitlements = [
        StubEntitlementCertificate(StubProduct(product_id_1), quantity=3),
        StubEntitlementCertificate(StubProduct(product_id_1), quantity=2),
        StubEntitlementCertificate(StubProduct(product_id_2), quantity=9),
    ]

    def test_if_not_multi_entitled_defualt_to_1(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: False,
                     QuantityDefaultValueCalculator._SOCKET_FACT_NAME: '1'}
        facts = StubFacts(fact_dict, facts_changed=False)

        calculator = QuantityDefaultValueCalculator(facts, [])
        calculator._get_total_consumed = zero_consumed

        pool = create_pool("my-test-product", "My Test Product")
        qty = calculator.calculate(pool)
        self.assertEquals(1, qty)

    def test_on_pysical_machine_default_to_num_sockets_by_socket_count(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: False,
                     QuantityDefaultValueCalculator._SOCKET_FACT_NAME: '4'}
        facts = StubFacts(fact_dict, facts_changed=False)
        calculator = QuantityDefaultValueCalculator(facts, [])
        calculator._get_total_consumed = zero_consumed

        self.assertFalse(calculator._is_virtual_machine())

        productAttrs = [create_attr("multi-entitlement", "yes"),
                        create_attr(QuantityDefaultValueCalculator._SOCKETS_PROD_ATTR_NAME, "2")]
        pool = create_pool("my-test-product", "My Test Product",
                           productAttributes=productAttrs)
        qty = calculator.calculate(pool)
        # ceil(m_sockets / p_socket)
        self.assertEquals(2, qty)

    def test_on_physical_machine_default_rounds_up(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: False,
                     QuantityDefaultValueCalculator._SOCKET_FACT_NAME: '4'}
        facts = StubFacts(fact_dict, facts_changed=False)

        calculator = QuantityDefaultValueCalculator(facts, [])
        calculator._get_total_consumed = zero_consumed

        self.assertFalse(calculator._is_virtual_machine())

        productAttrs = [create_attr("multi-entitlement", "yes"),
                        create_attr(QuantityDefaultValueCalculator._SOCKETS_PROD_ATTR_NAME, "3")]
        pool = create_pool("my-test-product", "My Test Product",
                           productAttributes=productAttrs)
        qty = calculator.calculate(pool)
        # ceil(m_sockets / p_socket)
        self.assertEquals(2, qty)

    def test_on_virtual_machine_default_to_num_cpus_by_cpu_count(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: True,
                     QuantityDefaultValueCalculator._CPUS_FACT_NAME: '8'}
        facts = StubFacts(fact_dict, facts_changed=False)

        calculator = QuantityDefaultValueCalculator(facts, [])
        calculator._get_total_consumed = zero_consumed

        self.assertTrue(calculator._is_virtual_machine())
        productAttrs = [create_attr("multi-entitlement", "yes"),
                        create_attr(QuantityDefaultValueCalculator._CPUS_PROD_ATTR_NAME, "4")]
        pool = create_pool("my-test-product", "My Test Product",
                           productAttributes=productAttrs)
        qty = calculator.calculate(pool)
        # ceil(m_cpus / p_cpus)
        self.assertEquals(2, qty)

    def test_on_virt_machine_default_rounds_up(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: True,
                     QuantityDefaultValueCalculator._CPUS_FACT_NAME: '8'}
        facts = StubFacts(fact_dict, facts_changed=False)

        calculator = QuantityDefaultValueCalculator(facts, [])
        calculator._get_total_consumed = zero_consumed

        self.assertTrue(calculator._is_virtual_machine())
        productAttrs = [create_attr("multi-entitlement", "yes"),
                        create_attr(QuantityDefaultValueCalculator._CPUS_PROD_ATTR_NAME, "6")]
        pool = create_pool("my-test-product", "My Test Product",
                           productAttributes=productAttrs)
        qty = calculator.calculate(pool)
        # ceil(m_cpus / p_cpus)
        self.assertEquals(2, qty)

    def test_is_vert_when_fact_is_defined_as_true(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: True}
        facts = StubFacts(fact_dict, facts_changed=False)
        calculator = QuantityDefaultValueCalculator(facts, [])
        self.assertTrue(calculator._is_virtual_machine())

    def test_is_not_vert_when_fact_is_defined_as_false(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: False}
        facts = StubFacts(fact_dict, facts_changed=False)
        calculator = QuantityDefaultValueCalculator(facts, [])
        self.assertFalse(calculator._is_virtual_machine())

    def test_is_not_vert_when_fact_is_not_defined(self):
        facts = StubFacts({}, facts_changed=False)
        calculator = QuantityDefaultValueCalculator(facts, [])
        self.assertFalse(calculator._is_virtual_machine())

    def test_is_not_vert_when_fact_is_defined_as_empty(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: ""}
        facts = StubFacts(fact_dict, facts_changed=False)
        calculator = QuantityDefaultValueCalculator(facts, [])
        self.assertFalse(calculator._is_virtual_machine())

    def test_get_total_consumed_adds_matched(self):
        calculator = QuantityDefaultValueCalculator(StubFacts({}), self.entitlements)
        self.assertEquals(5, calculator._get_total_consumed(self.product_id_1))

    def test_get_total_consumed_returns_zero_when_no_matches(self):
        calculator = QuantityDefaultValueCalculator(StubFacts({}), self.entitlements)
        self.assertEquals(0, calculator._get_total_consumed("does-not-match"))

    def test_calculated_value_is_zero_when_negative_value_is_calculated(self):
        fact_dict = {QuantityDefaultValueCalculator._VIRT_IS_GUEST_FACT_NAME: False,
                     QuantityDefaultValueCalculator._SOCKET_FACT_NAME: '4'}
        facts = StubFacts(fact_dict, facts_changed=False)
        calculator = QuantityDefaultValueCalculator(facts, [])
        calculator._get_total_consumed = ten_consumed

        self.assertFalse(calculator._is_virtual_machine())

        productAttrs = [create_attr("multi-entitlement", "yes"),
                        create_attr(QuantityDefaultValueCalculator._SOCKETS_PROD_ATTR_NAME, "2")]
        pool = create_pool("my-test-product", "My Test Product",
                           productAttributes=productAttrs)
        qty = calculator.calculate(pool)
        # 10 are already consumed, so 4/2 - 10 = -8
        self.assertEquals(0, qty)

def zero_consumed(product_id):
    return 0

def ten_consumed(product_id):
    return 10

def create_attr(name, value):
    return {"name": name, "value": value}
