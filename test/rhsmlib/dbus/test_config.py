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
from typing import Any, Dict

import dbus

from rhsm.config import RhsmConfigParser
from rhsmlib.dbus.objects.config import ConfigDBusObject
from test.rhsmlib.base import DBusServerStubProvider

from test.rhsmlib.services.test_config import TEST_CONFIG

TEST_CONFIG = """
[foo]
bar =
quux = baz
bigger_than_32_bit = 21474836470
bigger_than_64_bit = 123456789009876543211234567890

[server]
hostname = server.example.com
prefix = /candlepin
port = 8443
insecure = 1
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =

[rhsm]
ca_cert_dir = /etc/rhsm/ca-test/
baseurl = https://content.example.com
repomd_gpg_url =
repo_ca_cert = %(ca_cert_dir)sredhat-uep-non-default.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer
report_package_profile = 1
pluginDir = /usr/lib/rhsm-plugins
some_option = %(repo_ca_cert)stest
manage_repos =

[rhsmcertd]
certCheckInterval = 245

[logging]
default_log_level = DEBUG
"""


class TestConfigDBusObject(DBusServerStubProvider):
    dbus_class = ConfigDBusObject
    dbus_class_kwargs: Dict[str, Any] = {"parser": None}

    config_file = None
    """Attribute referencing file containing test configuration text."""

    parser = None
    """Attribute referencing configuration's parser object."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config_file = tempfile.NamedTemporaryFile()
        with open(cls.config_file.name, "w") as handle:
            handle.write(TEST_CONFIG)
        cls.parser = RhsmConfigParser(cls.config_file.name)
        cls.dbus_class_kwargs["parser"] = cls.parser

        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.config_file = None
        super().tearDownClass()

    def test_GetAll(self):
        result = self.obj.GetAll.__wrapped__(self.obj, self.LOCALE)
        self.assertIn("server", result.keys())

    def test_Get__property(self):
        result = self.obj.Get.__wrapped__(self.obj, "server.hostname", self.LOCALE)
        self.assertEqual("server.example.com", result)

    def test_Get__section(self):
        result = self.obj.Get.__wrapped__(self.obj, "server", self.LOCALE)
        self.assertIn("hostname", result.keys())

    def test_Set(self):
        original: str = self.parser.get("server", "hostname")

        self.obj.Set.__wrapped__(self.obj, "server.hostname", "new", self.LOCALE)
        self.assertEqual("new", self.parser.get("server", "hostname"))

        self.parser.set("server", "hostname", original)

    def test_Set__section_fails(self):
        with self.assertRaisesRegex(dbus.DBusException, "Setting an entire section is not supported.*"):
            self.obj.Set.__wrapped__(self.obj, "server", "new", self.LOCALE)
