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
from stubs import StubEntitlementCertificate, StubProduct
from subscription_manager.cert_sorter import EntitlementCertStackingGroupSorter

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
