# Copyright (c) 2016 Red Hat, Inc.
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

from rhsmlib.dbus.facts.base import AllFacts

from test.rhsmlib.base import DBusServerStubProvider


class TestFactsDBusObject(DBusServerStubProvider):
    dbus_class = AllFacts
    dbus_class_kwargs = {}

    @classmethod
    def setUpClass(cls) -> None:
        # Do not try to use system virt-what
        get_virt_info_patch = mock.patch(
            "rhsmlib.facts.virt.VirtWhatCollector.get_virt_info",
            name="get_virt_info",
        )
        cls.patches["get_virt_info"] = get_virt_info_patch.start()
        cls.patches["get_virt_info"].return_value = {}
        cls.addClassCleanup(get_virt_info_patch.stop)

        # Do not collect network facts, as they can cause issues in containers
        get_network_info_patch = mock.patch(
            "rhsmlib.facts.hwprobe.HardwareCollector.get_network_info",
            name="get_network_info",
        )
        cls.patches["get_network_info"] = get_network_info_patch.start()
        cls.patches["get_network_info"].return_value = {}
        cls.addClassCleanup(get_network_info_patch.stop)

        super().setUpClass()

    def setUp(self) -> None:
        self.patches["get_virt_info"].return_value = {"virt.is_guest": "Unknown"}

        super().setUp()

    def test_GetFacts(self):
        expected = "uname.machine"
        result = self.obj.GetFacts.__wrapped__(self.obj)
        self.assertIn(expected, result)
