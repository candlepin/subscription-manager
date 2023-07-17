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
import dbus
from unittest import mock

from rhsmlib.dbus.objects.unregister import UnregisterDBusImplementation

from test.rhsmlib.base import SubManDBusFixture


class TestUnregisterDBusObject(SubManDBusFixture):
    def setUp(self) -> None:
        super().setUp()
        self.impl = UnregisterDBusImplementation()

        is_registered_patch = mock.patch(
            "rhsmlib.dbus.base_object.BaseImplementation.is_registered",
            name="is_registered",
        )
        self.patches["is_registered"] = is_registered_patch.start()
        self.addCleanup(is_registered_patch.stop)

    def test_Unregister__must_be_registered(self):
        self.patches["is_registered"].return_value = False

        with self.assertRaisesRegex(dbus.DBusException, r"requires the consumer to be registered.*"):
            self.impl.unregister({})
