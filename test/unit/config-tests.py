#
# Copyright (c) 2011 - 2012 Red Hat, Inc.
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

from iniparse.compat import NoOptionError
from tempfile import NamedTemporaryFile
import types
import unittest


from rhsm.config import RhsmConfigParser

TEST_CONFIG = """
[foo]
bar =
bigger_than_32_bit = 21474836470
bigger_than_64_bit = 123456789009876543211234567890
[server]
hostname = server.example.conf
prefix = /candlepin
port = 8443
insecure = 1
ssl_verify_depth = 3
ca_cert_dir = /etc/rhsm/ca/
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =

[rhsm]
baseurl= https://content.example.com
repo_ca_cert = %(ca_cert_dir)sredhat-uep.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer
report_package_profile = 1
pluginDir = /usr/lib/rhsm-plugins

[rhsmcertd]
certCheckInterval = 240
"""


class ConfigTests(unittest.TestCase):

    def setUp(self):
        # create a temp file for use as a config file. This should get cleaned
        # up magically at the end of the run.
        self.fid = NamedTemporaryFile(mode='w+b', suffix='.tmp')
        self.fid.write(TEST_CONFIG)
        self.fid.seek(0)

        self.cfgParser = RhsmConfigParser(self.fid.name)

    def testRead(self):
        self.assertEquals(self.cfgParser.get('server', 'hostname'), 'server.example.conf')

    def testSet(self):
        self.cfgParser.set('rhsm', 'baseurl', 'cod')
        self.assertEquals(self.cfgParser.get('rhsm', 'baseurl'), 'cod')

    def test_get(self):
        value = self.cfgParser.get("rhsm", "baseurl")
        self.assertEquals("https://content.example.com", value)

    def test_get_empty(self):
        value = self.cfgParser.get("foo", "bar")
        self.assertEquals("", value)

    def test_get_int(self):
        value = self.cfgParser.get_int("server", "port")
        self.assertTrue(isinstance(value, types.IntType))
        self.assertEquals(8443, value)

    def test_get_item_does_not_exist(self):
        self.assertRaises(NoOptionError,
                          self.cfgParser.get,
                          "rhsm",
                          "this_isnt_a_thing")

    def test_get_int_un_set(self):
        value = self.cfgParser.get_int("server", "proxy_port")
        self.assertEquals(None, value)

    def test_get_int_does_not_exist(self):
        self.assertRaises(NoOptionError,
                          self.cfgParser.get_int,
                          "rhsm",
                          "this_isnt_a_thing")

    def test_get_int_not_an_int(self):
        self.assertRaises(ValueError,
                          self.cfgParser.get_int,
                          "rhsm",
                          "baseurl")

    def test_get_int_big_int(self):
        value = self.cfgParser.get_int("foo", "bigger_than_32_bit")
        self.assertEquals(21474836470, value)
        value = self.cfgParser.get_int("foo", "bigger_than_64_bit")
        self.assertEquals(123456789009876543211234567890, value)
