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
from modelhelpers import create_pool
from subscription_manager.quantity import QuantityDefaultValueCalculator, allows_multi_entitlement, \
                                            valid_quantity


class TestQuantityDefaultValueCalculator(unittest.TestCase):
    def test_uses_calculated_attributes(self):
        calculator = QuantityDefaultValueCalculator()
        pool = create_pool("my-test-product", "My Test Product",
                           calculatedAttributes={'suggested_quantity': 100})
        qty = calculator.calculate(pool)
        self.assertEquals(100, qty)

    def test_uses_default_for_empty_calculated_attributes(self):
        calculator = QuantityDefaultValueCalculator()
        pool = create_pool("my-test-product", "My Test Product",
                           calculatedAttributes={})
        qty = calculator.calculate(pool)
        self.assertEquals(1, qty)

    def test_if_not_multi_entitled_defualt_to_1(self):
        calculator = QuantityDefaultValueCalculator()
        pool = create_pool("my-test-product", "My Test Product")
        qty = calculator.calculate(pool)
        self.assertEquals(1, qty)

    def test_get_total_consumed_returns_zero_when_no_matches(self):
        calculator = QuantityDefaultValueCalculator()
        self.assertEquals(1, calculator.calculate("does-not-match"))


class TestAllowsMutliEntitlement(unittest.TestCase):

    def test_allows_when_yes(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("yes")
        self.assertTrue(allows_multi_entitlement(pool))

    def test_allows_when_1(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("1")
        self.assertTrue(allows_multi_entitlement(pool))

    def test_does_not_allow_when_no(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("no")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_0(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("0")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_not_set(self):
        pool = {"productAttributes": []}
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_empty_string(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_any_other_value(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("not_a_good_value")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_is_case_insensitive(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("YeS")
        self.assertTrue(allows_multi_entitlement(pool))

        pool = self._create_pool_data_with_multi_entitlement_attribute("nO")
        self.assertFalse(allows_multi_entitlement(pool))

    def _create_pool_data_with_multi_entitlement_attribute(self, value):
        return {"productAttributes": [{"name": "multi-entitlement", "value": value}]}


class TestValidQuantity(unittest.TestCase):
    def test_nonetype_not_valid(self):
        self.assertFalse(valid_quantity(None))

    def test_neg_quantity_value_is_invalid(self):
        self.assertFalse(valid_quantity(-1))

    def test_positive_quantity_value_is_valid(self):
        self.assertTrue(valid_quantity(3))

    def test_string_quantity_not_valid(self):
        self.assertFalse(valid_quantity("12dfg2"))
