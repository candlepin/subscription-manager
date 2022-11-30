# Copyright (c) 2017 Red Hat, Inc.
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
from unittest import mock
import json

from rhsmlib.dbus.objects import EntitlementDBusObject

from test.rhsmlib.base import DBusServerStubProvider


class TestEntitlementDBusObject(DBusServerStubProvider):
    dbus_class = EntitlementDBusObject
    dbus_class_kwargs = {}

    def test_GetStatus(self):
        get_status_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.get_status",
            name="get_status",
        )
        self.patches["get_status_patch"] = get_status_patch.start()
        self.addCleanup(get_status_patch.stop)

        status = {"status": "Unknown", "reasons": {}, "valid": False}
        self.patches["get_status_patch"].return_value = status

        expected = json.dumps(status)
        result = self.obj.GetStatus.__wrapped__(self.obj, "", self.LOCALE)
        self.assertEqual(expected, result)

    def test_RemoveEntitlementsBySerials(self):
        remove_entitlements_by_serials_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.remove_entitlements_by_serials",
            name="remove_entitlements_by_serials",
        )
        self.patches["remove_entitlements_by_serials"] = remove_entitlements_by_serials_patch.start()
        self.addCleanup(remove_entitlements_by_serials_patch.stop)

        removed_nonremoved = (["123"], [])
        self.patches["remove_entitlements_by_serials"].return_value = removed_nonremoved

        expected = json.dumps(removed_nonremoved[0])
        result = self.obj.RemoveEntitlementsBySerials.__wrapped__(self.obj, ["123"], {}, self.LOCALE)
        self.assertEqual(expected, result)

    def test_RemoveEntitlementsBySerials__multiple(self):
        remove_entitlements_by_serials_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.remove_entitlements_by_serials",
            name="remove_entitlements_by_serials",
        )
        self.patches["remove_entitlements_by_serials"] = remove_entitlements_by_serials_patch.start()
        self.addCleanup(remove_entitlements_by_serials_patch.stop)

        removed_nonremoved = (["123", "456"], [])
        self.patches["remove_entitlements_by_serials"].return_value = removed_nonremoved

        expected = json.dumps(removed_nonremoved[0])
        result = self.obj.RemoveEntitlementsBySerials.__wrapped__(self.obj, ["123", "456"], {}, self.LOCALE)
        self.assertEqual(expected, result)

    def test_RemoveEntitlementsBySerials__good_and_bad(self):
        remove_entitlements_by_serials_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.remove_entitlements_by_serials",
            name="remove_entitlements_by_serials",
        )
        self.patches["remove_entitlements_by_serials"] = remove_entitlements_by_serials_patch.start()
        self.addCleanup(remove_entitlements_by_serials_patch.stop)

        removed_nonremoved = (["123"], ["456"])
        self.patches["remove_entitlements_by_serials"].return_value = removed_nonremoved

        expected = json.dumps(removed_nonremoved[0])
        result = self.obj.RemoveEntitlementsBySerials.__wrapped__(self.obj, ["123", "789"], {}, self.LOCALE)
        self.assertEqual(expected, result)

    def test_RemoveEntitlementsByPoolIds(self):
        remove_entitlements_by_pool_ids_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.remove_entitlements_by_pool_ids",
            name="remove_entitlements_by_pool_ids",
        )
        self.patches["remove_entitlements_by_pool_ids"] = remove_entitlements_by_pool_ids_patch.start()
        self.addCleanup(remove_entitlements_by_pool_ids_patch.stop)

        removed_nonremoved_serials = (["123"], [], ["456"])
        self.patches["remove_entitlements_by_pool_ids"].return_value = removed_nonremoved_serials

        expected = json.dumps(removed_nonremoved_serials[2])
        result = self.obj.RemoveEntitlementsByPoolIds.__wrapped__(self.obj, ["123"], {}, self.LOCALE)
        self.assertEqual(expected, result)

    def test_RemoveAllEntitlements(self):
        remove_all_entitlements_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.remove_all_entitlements",
            name="remove_all_entitlements",
        )
        self.patches["remove_all_entitlements"] = remove_all_entitlements_patch.start()
        self.addCleanup(remove_all_entitlements_patch.stop)

        records = {"deletedRecords": 1}
        self.patches["remove_all_entitlements"].return_value = records

        expected = json.dumps(records)
        result = self.obj.RemoveAllEntitlements.__wrapped__(self.obj, {}, self.LOCALE)
        self.assertEqual(expected, result)
