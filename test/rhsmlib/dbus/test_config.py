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
import tempfile

import dbus

from rhsm.config import RhsmConfigParser
from rhsmlib.dbus.objects.config import ConfigDBusImplementation
from test.rhsmlib.base import SubManDBusFixture

from test.rhsmlib.services.test_config import TEST_CONFIG


class TestConfigDBusObject(SubManDBusFixture):
    config_file = None
    """Attribute referencing file containing test configuration text."""
    parser = None
    """Attribute referencing configuration's parser object."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.config_file = tempfile.NamedTemporaryFile()
        with open(cls.config_file.name, "w") as handle:
            handle.write(TEST_CONFIG)
        cls.parser = RhsmConfigParser(cls.config_file.name)

        cls.impl = ConfigDBusImplementation(cls.parser)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.config_file = None
        super().tearDownClass()

    def test_GetAll(self):
        result = self.impl.get_all()
        self.assertIn("server", result.keys())

    def test_Get__property(self):
        result = self.impl.get("server.hostname")
        self.assertEqual("server.example.com", result)

    def test_Get__section(self):
        result = self.impl.get("server")
        self.assertIn("hostname", result.keys())

    def test_Set(self):
        original: str = self.parser.get("server", "hostname")

        self.impl.set("server.hostname", "new")
        self.assertEqual("new", self.parser.get("server", "hostname"))

        self.parser.set("server", "hostname", original)

    def test_Set__section_fails(self):
        with self.assertRaisesRegex(dbus.DBusException, "Setting an entire section is not supported.*"):
            self.impl.set("server", "new")
