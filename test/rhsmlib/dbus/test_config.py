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

import dbus

from rhsm.config import RhsmConfigParser
from rhsmlib.dbus import constants
from rhsmlib.dbus.objects.config import ConfigDBusObject
from test.rhsmlib.base import DBusObjectTest, TestUtilsMixin

from test.rhsmlib.services.test_config import TEST_CONFIG
from test import subman_marker_dbus


@subman_marker_dbus
class TestConfigDBusObject(DBusObjectTest, TestUtilsMixin):
    def setUp(self):
        super(TestConfigDBusObject, self).setUp()
        self.proxy = self.proxy_for(ConfigDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.CONFIG_INTERFACE)

    def dbus_objects(self):
        self.fid = self.write_temp_file(TEST_CONFIG)
        self.addCleanup(self.fid.close)
        self.parser = RhsmConfigParser(self.fid.name)
        return [(ConfigDBusObject, {"parser": self.parser})]

    def test_get_all(self):
        def assertions(*args):
            result = args[0]
            self.assertIn("server", result)

        dbus_method_args = [""]
        self.dbus_request(assertions, self.interface.GetAll, dbus_method_args)

    def test_get_property(self):
        def assertions(*args):
            result = args[0]
            self.assertIn("server.example.com", result)

        dbus_method_args = ["server.hostname", ""]
        self.dbus_request(assertions, self.interface.Get, dbus_method_args)

    def test_get_section(self):
        def assertions(*args):
            result = args[0]
            self.assertIn("hostname", result)

        dbus_method_args = ["server", ""]
        self.dbus_request(assertions, self.interface.Get, dbus_method_args)

    def test_set(self):
        def assertions(*args):
            self.assertEqual("new", self.parser.get("server", "hostname"))

        dbus_method_args = ["server.hostname", "new", ""]
        self.dbus_request(assertions, self.interface.Set, dbus_method_args)

    def test_set_section_fails(self):
        dbus_method_args = ["server", "new", ""]

        with self.assertRaisesRegex(dbus.DBusException, r"Setting an entire section is not.*"):
            self.dbus_request(None, self.interface.Set, dbus_method_args)
