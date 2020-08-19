from __future__ import print_function, division, absolute_import

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
#
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import dbus
import six

from rhsm.config import RhsmConfigParser, NoOptionError
from rhsmlib.dbus import constants
from rhsmlib.dbus.objects.config import ConfigDBusObject
from rhsmlib.services.config import Config, ConfigSection
from test.rhsmlib_test.base import DBusObjectTest, TestUtilsMixin

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
ssl_verify_depth = 3
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


class BaseConfigTest(unittest.TestCase, TestUtilsMixin):
    expected_sections = ['foo', 'server', 'rhsm', 'rhsmcertd', 'logging']

    def setUp(self):
        super(BaseConfigTest, self).setUp()
        self.fid = self.write_temp_file(TEST_CONFIG)
        self.parser = RhsmConfigParser(self.fid.name)
        self.config = Config(self.parser)
        self.addCleanup(self.fid.close)


class TestConfig(BaseConfigTest):
    def test_config_contains(self):
        self.assertTrue('server' in self.config)
        self.assertFalse('not_here' in self.config)

    def test_config_len(self):
        self.assertEqual(len(self.expected_sections), len(self.config))

    def test_keys(self):
        self.assert_items_equals(self.expected_sections, list(self.config.keys()))

    def test_values(self):
        values = list(self.config.values())
        for v in values:
            self.assertIsInstance(v, ConfigSection)

    def test_set_new_section(self):
        self.config['new_section'] = {'hello': 'world'}
        self.assertEqual(['hello'], self.config._parser.options('new_section'))
        self.assertEqual('world', self.config._parser.get('new_section', 'hello'))

    def test_set_old_section(self):
        self.config['foo'] = {'hello': 'world'}
        self.assertEqual(['hello'], self.config._parser.options('foo'))
        self.assertEqual('world', self.config._parser.get('foo', 'hello'))
        self.assertRaises(NoOptionError, self.config._parser.get, 'foo', 'quux')

    def test_get_item(self):
        self.assertIsInstance(self.config['server'], ConfigSection)

    def test_persist(self):
        self.config['foo'] = {'hello': 'world'}
        self.config.persist()
        reparsed = RhsmConfigParser(self.fid.name)
        self.assertEqual('world', reparsed.get('foo', 'hello'))
        self.assertRaises(NoOptionError, reparsed.get, 'foo', 'quux')

    def test_auto_persists(self):
        config = Config(self.parser, auto_persist=True)
        config['foo'] = {'hello': 'world'}
        reparsed = RhsmConfigParser(self.fid.name)
        self.assertEqual('world', reparsed.get('foo', 'hello'))
        self.assertRaises(NoOptionError, reparsed.get, 'foo', 'quux')

    def test_does_not_auto_persist_by_default(self):
        config = Config(self.parser, auto_persist=False)
        config['foo'] = {'hello': 'world'}
        reparsed = RhsmConfigParser(self.fid.name)
        self.assertEqual('baz', reparsed.get('foo', 'quux'))
        self.assertRaises(NoOptionError, reparsed.get, 'foo', 'hello')

    def test_del_item(self):
        del self.config['foo']
        self.assertFalse(self.config._parser.has_section('foo'))

    def test_iter(self):
        sections = [s for s in self.config]
        self.assert_items_equals(self.expected_sections, sections)


class TestConfigSection(BaseConfigTest):
    def test_get_value(self):
        self.assertEqual('1', self.config['server']['insecure'])

    def test_get_missing_value(self):
        with self.assertRaises(KeyError):
            self.config['server']['missing']

    def test_set_item(self):
        self.assertEqual('baz', self.config['foo']['quux'])
        self.config['foo']['quux'] = 'fizz'
        self.assertEqual('fizz', self.config['foo']['quux'])

    def test_auto_persist(self):
        config = Config(self.parser, auto_persist=True)
        self.assertEqual('baz', config['foo']['quux'])
        config['foo']['quux'] = 'fizz'
        self.assertEqual('fizz', config['foo']['quux'])

        reparsed = RhsmConfigParser(self.fid.name)
        self.assertEqual('fizz', reparsed.get('foo', 'quux'))

    def test_persist_cascades(self):
        config = Config(self.parser, auto_persist=False)
        self.assertEqual('baz', config['foo']['quux'])
        config['foo']['quux'] = 'fizz'
        config.persist()
        self.assertEqual('fizz', config['foo']['quux'])

        reparsed = RhsmConfigParser(self.fid.name)
        self.assertEqual('fizz', reparsed.get('foo', 'quux'))

    def test_del_item(self):
        del self.config['foo']['quux']
        self.assertNotIn('quux', self.config['foo'])

        with self.assertRaises(KeyError):
            del self.config['foo']['missing_key']

    def test_len(self):
        self.assertEqual(4, len(self.config['foo']))

    def test_in(self):
        self.assertIn("quux", self.config['foo'])
        self.assertNotIn("missing", self.config['foo'])


class TestConfigDBusObject(DBusObjectTest, TestUtilsMixin):
    def setUp(self):
        super(TestConfigDBusObject, self).setUp()
        self.proxy = self.proxy_for(ConfigDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.CONFIG_INTERFACE)

    def dbus_objects(self):
        self.fid = self.write_temp_file(TEST_CONFIG)
        self.addCleanup(self.fid.close)
        self.parser = RhsmConfigParser(self.fid.name)
        return [(ConfigDBusObject, {'parser': self.parser})]

    def test_get_all(self):
        def assertions(*args):
            result = args[0]
            self.assertIn("server", result)

        dbus_method_args = ['']
        self.dbus_request(assertions, self.interface.GetAll, dbus_method_args)

    def test_get_property(self):
        def assertions(*args):
            result = args[0]
            self.assertIn('server.example.com', result)

        dbus_method_args = ['server.hostname', '']
        self.dbus_request(assertions, self.interface.Get, dbus_method_args)

    def test_get_section(self):
        def assertions(*args):
            result = args[0]
            self.assertIn('hostname', result)

        dbus_method_args = ['server', '']
        self.dbus_request(assertions, self.interface.Get, dbus_method_args)

    def test_set(self):
        def assertions(*args):
            self.assertEqual('new', self.parser.get('server', 'hostname'))

        dbus_method_args = ['server.hostname', 'new', '']
        self.dbus_request(assertions, self.interface.Set, dbus_method_args)

    def test_set_section_fails(self):
        dbus_method_args = ['server', 'new', '']

        with six.assertRaisesRegex(self, dbus.DBusException, r'Setting an entire section is not.*'):
            self.dbus_request(None, self.interface.Set, dbus_method_args)
