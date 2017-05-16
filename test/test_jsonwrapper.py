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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from .modelhelpers import create_pool, create_attribute_list
from subscription_manager.jsonwrapper import PoolWrapper


class TestPoolWrapper(unittest.TestCase):

    def _create_wrapper(self, add_is_virt_only=False, is_virt_only_value="true",
                        add_stacking_id=False, stacking_id=None, pool_type=None,
                        add_management_enabled=False, management_enabled_value="true"):
        attrs = {}
        if add_is_virt_only:
            attrs['virt_only'] = is_virt_only_value

        prod_attrs = {}
        if add_stacking_id:
            prod_attrs['stacking_id'] = stacking_id

        if add_management_enabled:
            prod_attrs['management_enabled'] = management_enabled_value

        calculatedAttributes = None
        if pool_type:
            calculatedAttributes = {'compliance_type': pool_type}
        pool = create_pool("pid", "pname", attributes=create_attribute_list(attrs),
                           productAttributes=create_attribute_list(prod_attrs),
                           calculatedAttributes=calculatedAttributes)
        return PoolWrapper(pool)

    def test_is_not_virt_only_when_attribute_is_false(self):
        wrapper = self._create_wrapper(add_is_virt_only=True, is_virt_only_value="false")
        self.assertFalse(wrapper.is_virt_only())

    def test_is_virt_only_when_attribute_is_true(self):
        wrapper = self._create_wrapper(add_is_virt_only=True, is_virt_only_value="true")
        self.assertTrue(wrapper.is_virt_only())

    def test_is_virt_only_when_attribute_is_1(self):
        wrapper = self._create_wrapper(add_is_virt_only=True, is_virt_only_value="1")
        self.assertTrue(wrapper.is_virt_only())

    def test_is_not_virt_only_when_attribute_is_0(self):
        wrapper = self._create_wrapper(add_is_virt_only=True, is_virt_only_value="0")
        self.assertFalse(wrapper.is_virt_only())

    def test_is_virt_only_when_attribute_is_not_set(self):
        wrapper = self._create_wrapper()
        self.assertFalse(wrapper.is_virt_only())

    def test_get_stacking_id_when_attribute_is_set(self):
        wrapper = self._create_wrapper(add_stacking_id=True, stacking_id="1234")
        self.assertEqual("1234", wrapper.get_stacking_id())

    def test_get_stacking_id_when_attribute_not_set(self):
        wrapper = self._create_wrapper(add_stacking_id=True)
        self.assertEqual(None, wrapper.get_stacking_id())

    def test_none_when_stacking_id_empty(self):
        wrapper = self._create_wrapper(add_stacking_id=True, stacking_id="")
        self.assertEqual(None, wrapper.get_stacking_id())

    def test_compliance_type(self):
        wrapper = self._create_wrapper(pool_type='double stackable')
        self.assertEqual('double stackable', wrapper.get_pool_type())

    def test_no_compliance_type(self):
        wrapper = self._create_wrapper()
        self.assertEqual('', wrapper.get_pool_type())

    def test_management_enabled_when_attribute_is_false(self):
        wrapper = self._create_wrapper(add_management_enabled=True, management_enabled_value="false")
        self.assertFalse(wrapper.management_enabled())

    def test_management_enabled_when_attribute_is_true(self):
        wrapper = self._create_wrapper(add_management_enabled=True, management_enabled_value="true")
        self.assertTrue(wrapper.management_enabled())

    def test_management_enabled_when_attribute_is_1(self):
        wrapper = self._create_wrapper(add_management_enabled=True, management_enabled_value="1")
        self.assertTrue(wrapper.management_enabled())

    def test_management_enabled_when_attribute_is_0(self):
        wrapper = self._create_wrapper(add_management_enabled=True, management_enabled_value="0")
        self.assertFalse(wrapper.management_enabled())

    def test_management_enabled_when_attribute_is_not_set(self):
        wrapper = self._create_wrapper()
        self.assertFalse(wrapper.management_enabled())
