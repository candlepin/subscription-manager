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
from rhsmlib.dbus.objects.entitlement import EntitlementDBusImplementation

from unittest import mock
from test.rhsmlib.base import SubManDBusFixture


class TestEntitlementDBusObject(SubManDBusFixture):
    def setUp(self):
        super().setUp()
        self.impl = EntitlementDBusImplementation()

    def test_get_status(self):
        get_status_patch = mock.patch(
            "rhsmlib.services.entitlement.EntitlementService.get_status",
            name="get_status",
        )
        self.patches["get_status_patch"] = get_status_patch.start()
        self.addCleanup(get_status_patch.stop)

        expected = {"status": "Unknown", "reasons": {}, "valid": False}
        self.patches["get_status_patch"].return_value = expected

        result = self.impl.get_status("")
        self.assertEqual(expected, result)
