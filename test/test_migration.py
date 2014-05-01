#
# Copyright (c) 2012 Red Hat, Inc.
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

from mock import patch, NonCallableMock, MagicMock, call
from M2Crypto import SSL
import re
import sys
import StringIO
import unittest

import stubs

from fixture import Capture
import fixture


import rhsm.config
from subscription_manager import injection as inj
from subscription_manager.migrate import migrate
from subscription_manager import identity
from subscription_manager.certdirectory import ProductDirectory


class TestMenu(unittest.TestCase):
    def setUp(self):
        self.menu = migrate.Menu([
            ("displayed-hello", "Hello"),
            ("displayed-world", "World"),
            ], "")
        sys.stderr = stubs.MockStderr()

    def tearDown(self):
        sys.stderr = sys.__stderr__

    def test_enter_negative(self):
        self.assertRaises(migrate.InvalidChoiceError, self.menu._get_item, -1)

    def test_enter_nonnumber(self):
        self.assertRaises(migrate.InvalidChoiceError, self.menu._get_item, "a")

    def test_get_item(self):
        self.assertEqual("Hello", self.menu._get_item(1))

    @patch("__builtin__.raw_input")
    @patch.object(migrate.Menu, "display_invalid")
    def test_choose(self, mock_display_invalid, mock_input):
        mock_input.side_effect = ["9000", "1"]
        choice = self.menu.choose()

        mock_display_invalid.assert_called_once_with()
        self.assertEqual(choice, "Hello")


class TestMigration(fixture.SubManFixture):
    def create_options(self, *options):
        """
        Create a mock options object.  Send in a dictionary with the option names and values
        and they will be set.  For options that should be None, just send in a list of the
        option names.
        """
        mock_opts = MagicMock()
        for entry in options:
            if isinstance(entry, dict):
                [setattr(mock_opts, k, v) for k, v in entry.items()]
            else:
                [setattr(mock_opts, x, None) for x in entry]
        return mock_opts

    def setUp(self):
        super(TestMigration, self).setUp()
        migrate.initUp2dateConfig = lambda: {}
        patch('subscription_manager.migrate.migrate.ProductDatabase').start()
        self.engine = migrate.MigrationEngine()
        self.engine.cp = stubs.StubUEP()

        # These tests print a lot to stdout and stderr
        # so quiet them.
        sys.stderr = stubs.MockStderr()

        self.double_mapped_channels = (
            "rhel-i386-client-dts-5-beta",
            "rhel-i386-client-dts-5-beta-debuginfo",
            "rhel-i386-server-dts-5-beta",
            "rhel-i386-server-dts-5-beta-debuginfo",
            "rhel-x86_64-client-dts-5-beta",
            "rhel-x86_64-client-dts-5-beta-debuginfo",
            "rhel-x86_64-server-dts-5-beta",
            "rhel-x86_64-server-dts-5-beta-debuginfo",
            )
        self.single_mapped_channels = (
            "rhel-i386-client-dts-5",
            "rhel-i386-client-dts-5-debuginfo",
            "rhel-x86_64-client-dts-5",
            "rhel-x86_64-client-dts-5-debuginfo",
            "rhel-i386-server-dts-5",
            "rhel-i386-server-dts-5-debuginfo",
            "rhel-x86_64-server-dts-5",
            "rhel-x86_64-server-dts-5-debuginfo",
            )

    def tearDown(self):
        patch.stopall()
        sys.stderr = sys.__stderr__

    def test_mutually_exclusive_options(self):
        try:
            self.engine.main(["--no-auto", "--servicelevel", "foo"])
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    @patch.object(rhsm.config.RhsmConfigParser, "get")
    def test_is_hosted(self, mock_get):
        mock_get.return_value = "subscription.rhn.redhat.com"
        self.assertTrue(self.engine.is_hosted())

    @patch.object(rhsm.config.RhsmConfigParser, "get")
    def test_is_not_hosted(self, mock_get):
        mock_get.return_value = "subscription.example.com"
        self.assertFalse(self.engine.is_hosted())

    @patch("__builtin__.raw_input")
    @patch("getpass.getpass")
    def test_authenticate(self, mock_getpass, mock_input):
        mock_input.return_value = "username"
        mock_getpass.return_value = "password"
        creds = self.engine.authenticate(None, None, "Some prompt", "Some other prompt")
        self.assertEquals(creds.username, "username")
        self.assertEquals(creds.password, "password")

    def test_authenticate_when_values_given(self):
        creds = self.engine.authenticate("username", "password", "Some prompt", "Some other prompt")
        self.assertEquals(creds.username, "username")
        self.assertEquals(creds.password, "password")

    @patch("__builtin__.raw_input")
    @patch("getpass.getpass")
    def test_get_auth_with_serverurl(self, mock_getpass, mock_input):
        self.engine.options = self.create_options({'serverurl': 'foobar'},
            ["redhatuser", "redhatpassword", "subserviceuser", "subservicepassword"])

        mock_input.side_effect = ["rhn_username", "se_username"]
        mock_getpass.side_effect = ["rhn_password", "se_password"]

        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "se_username")
        self.assertEquals(self.engine.secreds.password, "se_password")

    @patch("__builtin__.raw_input")
    @patch("getpass.getpass")
    def test_get_auth_without_serverurl_and_not_hosted(self, mock_getpass, mock_input):
        self.engine.options = self.create_options(["serverurl", "redhatuser",
            "redhatpassword", "subserviceuser", "subservicepassword"])

        mock_input.side_effect = ["rhn_username", "se_username"]
        mock_getpass.side_effect = ["rhn_password", "se_password"]

        self.engine.is_hosted = lambda: False
        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "se_username")
        self.assertEquals(self.engine.secreds.password, "se_password")

    @patch("__builtin__.raw_input")
    @patch("getpass.getpass")
    def test_get_auth_without_serverurl_and_is_hosted(self, mock_getpass, mock_input):
        self.engine.options = self.create_options(["serverurl", "redhatuser",
            "redhatpassword", "subserviceuser", "subservicepassword"])

        mock_input.return_value = "rhn_username"
        mock_getpass.return_value = "rhn_password"

        self.engine.is_hosted = lambda: True
        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "rhn_username")
        self.assertEquals(self.engine.secreds.password, "rhn_password")

    def test_get_auth_with_provided_rhn_creds(self):
        self.engine.options = self.create_options(
            {'redhatuser': 'rhn_username', 'redhatpassword': 'rhn_password'},
            ["serverurl", "subserviceuser", "subservicepassword"])
        self.engine.is_hosted = lambda: True
        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "rhn_username")
        self.assertEquals(self.engine.secreds.password, "rhn_password")

    @patch("getpass.getpass")
    def test_gets_password_when_only_username_give(self, mock_getpass):
        self.engine.options = self.create_options(
            {'redhatuser': 'rhn_username'},
            ["serverurl", "redhatpassword", "subserviceuser", "subservicepassword"])

        mock_getpass.return_value = "rhn_password"
        self.engine.is_hosted = lambda: True
        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "rhn_username")
        self.assertEquals(self.engine.secreds.password, "rhn_password")

    @patch("getpass.getpass")
    def test_gets_se_password_when_only_se_username_give(self, mock_getpass):
        self.engine.options = self.create_options(
            {'redhatuser': 'rhn_username', 'redhatpassword': 'rhn_password',
                'subserviceuser': 'se_username'},
            ["serverurl", "subservicepassword"])

        mock_getpass.return_value = "se_password"
        self.engine.is_hosted = lambda: False
        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "se_username")
        self.assertEquals(self.engine.secreds.password, "se_password")

    def test_all_auth_provided(self):
        self.engine.options = self.create_options(
            {'redhatuser': 'rhn_username', 'redhatpassword': 'rhn_password',
                'subserviceuser': 'se_username', 'subservicepassword': 'se_password'},
            ["serverurl"])

        self.engine.is_hosted = lambda: False
        self.engine.get_auth()
        self.assertEquals(self.engine.rhncreds.username, "rhn_username")
        self.assertEquals(self.engine.rhncreds.password, "rhn_password")
        self.assertEquals(self.engine.secreds.username, "se_username")
        self.assertEquals(self.engine.secreds.password, "se_password")

    def test_setting_unauthenticated_proxy(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options({'noproxy': False})

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "proxy.example.com:123",
            "enableProxyAuth": False,
            }
        self.engine.rhncfg = rhn_config
        self.engine.transfer_http_proxy_settings()
        expected = [call("server", "proxy_hostname", "proxy.example.com"),
            call("server", "proxy_port", "123"),
            call("server", "proxy_user", ""),
            call("server", "proxy_password", ""),
            ]
        self.assertTrue(self.engine.rhsmcfg.set.call_args_list == expected)
        self.engine.rhsmcfg.save.assert_called_once_with()

    def test_setting_authenticated_proxy(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options({'noproxy': False})

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "proxy.example.com:123",
            "enableProxyAuth": True,
            "proxyUser": "foo",
            "proxyPassword": "bar",
            }
        self.engine.rhncfg = rhn_config
        self.engine.transfer_http_proxy_settings()
        expected = [call("server", "proxy_hostname", "proxy.example.com"),
            call("server", "proxy_port", "123"),
            call("server", "proxy_user", "foo"),
            call("server", "proxy_password", "bar"),
            ]
        self.assertTrue(self.engine.rhsmcfg.set.call_args_list == expected)
        self.engine.rhsmcfg.save.assert_called_once_with()

    def test_setting_prefixed_proxy(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options({'noproxy': False})

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "http://proxy.example.com:123",
            "enableProxyAuth": False,
            }
        self.engine.rhncfg = rhn_config
        self.engine.transfer_http_proxy_settings()
        expected = [call("server", "proxy_hostname", "proxy.example.com"),
            call("server", "proxy_port", "123"),
            call("server", "proxy_user", ""),
            call("server", "proxy_password", ""),
            ]
        self.assertTrue(self.engine.rhsmcfg.set.call_args_list == expected)
        self.engine.rhsmcfg.save.assert_called_once_with()

    def test_noproxy_option(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options({'noproxy': True})

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "proxy.example.com:123",
            "enableProxyAuth": False,
            }
        self.engine.rhncfg = rhn_config
        self.engine.transfer_http_proxy_settings()
        expected = [call("server", "proxy_hostname", ""),
            call("server", "proxy_port", ""),
            call("server", "proxy_user", ""),
            call("server", "proxy_password", ""),
            ]
        self.assertTrue(self.engine.rhsmcfg.set.call_args_list == expected)
        self.assertEquals("proxy.example.com", self.engine.proxy_host)
        self.assertEquals("123", self.engine.proxy_port)
        self.assertEquals(None, self.engine.proxy_user)
        self.assertEquals(None, self.engine.proxy_pass)

    def _setup_rhsmcfg_mocks(self):
        self.engine.options = self.create_options(['serverurl'])

        self.engine.rhsmcfg = MagicMock()
        self.engine.rhsmcfg.get = MagicMock(side_effect=[
            "candlepin.example.com",
            "/candlepin",
            ])
        self.engine.rhsmcfg.get_int = MagicMock(side_effect=[443])

        expected = [call("server", "hostname"),
            call("server", "prefix"),
            ]

        get_int_expected = [call("server", "port")]

        return expected, get_int_expected

    def test_no_server_url_provided_basic_auth(self):
        expected, get_int_expected = self._setup_rhsmcfg_mocks()
        self.engine.get_candlepin_basic_auth_connection("some_username", "some_password")
        self.assertTrue(self.engine.rhsmcfg.get.call_args_list == expected)
        self.assertTrue(self.engine.rhsmcfg.get_int.call_args_list == get_int_expected)

    def test_no_server_url_provided_consumer_auth(self):
        expected, get_int_expected = self._setup_rhsmcfg_mocks()
        self.engine.get_candlepin_consumer_connection()
        self.assertTrue(self.engine.rhsmcfg.get.call_args_list == expected)
        self.assertTrue(self.engine.rhsmcfg.get_int.call_args_list == get_int_expected)

    def test_bad_server_url_basic_auth(self):
        try:
            self.engine.options = self.create_options({'serverurl': 'http://'})
            self.engine.get_candlepin_basic_auth_connection("some_username", "some_password")
        except SystemExit, e:
            self.assertEquals(e.code, -1)
        else:
            self.fail("No exception raised")

    def test_bad_server_url_consumer_auth(self):
        try:
            self.engine.options = self.create_options({'serverurl': 'http://'})
            self.engine.get_candlepin_consumer_connection()
        except SystemExit, e:
            self.assertEquals(e.code, -1)
        else:
            self.fail("No exception raised")

    # default injected identity is "valid"
    def test_already_registered_to_rhsm(self):
        try:
            self.engine.check_ok_to_proceed("some_username")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_ssl_error(self):
        self._inject_mock_invalid_consumer()
        self.engine.cp.getOwnerList = MagicMock(side_effect=SSL.SSLError)
        try:
            self.engine.check_ok_to_proceed("some_username")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_no_orgs(self):
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = []
        try:
            self.engine.get_org("some_username")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_one_org(self):
        self.engine.options = self.create_options(['org'])
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [{"key": "my_org", "displayName": "My Org"}]
        org = self.engine.get_org("some_username")
        self.assertEquals(org, "my_org")

    @patch("__builtin__.raw_input")
    def test_enter_org_key(self, mock_input):
        self.engine.options = self.create_options(['org'])
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        mock_input.return_value = "my_org"
        org = self.engine.get_org("some_username")
        self.assertEquals(org, "my_org")

    @patch("__builtin__.raw_input")
    def test_enter_org_name(self, mock_input):
        self.engine.options = self.create_options(['org'])
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        mock_input.return_value = "My Org"
        org = self.engine.get_org("some_username")
        self.assertEquals(org, "my_org")

    @patch("__builtin__.raw_input")
    def test_enter_bad_org(self, mock_input):
        self.engine.options = self.create_options(['org'])
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        mock_input.return_value = "Some other org"
        try:
            self.engine.get_org("some_username")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_org_option(self):
        self.engine.options = self.create_options({'org': 'my_org'})
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        org = self.engine.get_org("some_username")
        self.assertEquals(org, "my_org")

    def test_bad_org_option(self):
        self.engine.options = self.create_options({'org': 'nonsense'})
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        try:
            self.engine.get_org("some_username")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_environment_supported_exception(self):
        self.engine.cp.supports_resource = MagicMock(side_effect=Exception)
        try:
            self.engine.get_environment("some_org")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_environment_with_no_resource(self):
        self.engine.options = self.create_options(['environment'])
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = False
        env = self.engine.get_environment("some_org")
        self.assertEquals(env, None)

    def test_single_environment_requires_no_input(self):
        self.engine.options = self.create_options(['environment'])
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"}
            ]

        env = self.engine.get_environment("some_org")
        self.assertEquals(env, "My Environment")

    @patch("__builtin__.raw_input")
    def test_enter_environment_name(self, mock_input):
        self.engine.options = self.create_options(['environment'])
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment"},
            {"name": "Another Environment"},
            ]

        mock_input.return_value = "My Environment"
        env = self.engine.get_environment("some_org")
        self.assertEquals(env, "My Environment")

    @patch("__builtin__.raw_input")
    def test_enter_environment_label(self, mock_input):
        self.engine.options = self.create_options(['environment'])
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]

        mock_input.return_value = "my_environment"
        env = self.engine.get_environment("some_org")
        self.assertEquals(env, "My Environment")

    @patch("__builtin__.raw_input")
    def test_enter_environment_displayName(self, mock_input):
        self.engine.options = self.create_options(['environment'])
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "displayName": "my_environment"},
            {"name": "Another Environment", "displayName": "another_environment"},
            ]

        mock_input.return_value = "my_environment"
        env = self.engine.get_environment("some_org")
        self.assertEquals(env, "My Environment")

    @patch("__builtin__.raw_input")
    def test_enter_bad_environment(self, mock_input):
        self.engine.options = self.create_options(['environment'])
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True
        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]

        mock_input.return_value = "something else"
        try:
            self.engine.get_environment("some_org")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_environment_option(self):
        self.engine.options = self.create_options({'environment': 'My Environment'})
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True
        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]

        env = self.engine.get_environment("some_org")
        self.assertEquals(env, "My Environment")

    def test_bad_environment_option(self):
        self.engine.options = self.create_options({'environment': 'nonsense'})
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True
        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]
        try:
            self.engine.get_environment("some_org")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_environment_option_with_no_resource(self):
        self.engine.options = self.create_options({'environment': 'My Environment'})
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = False
        try:
            self.engine.get_environment("some_org")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    @patch("rhn.rpclib.Server")
    def test_connect_to_rhn(self, mock_server):
        rhn_config = {
            "serverURL": "https://some.host.example.com/XMLRPC",
            "enableProxy": True,
            "enableProxyAuth": True,
            "sslCACert": "/some/path/here",
            }
        self.engine.rhncfg = rhn_config
        self.engine.proxy_user = "proxy_user"
        self.engine.proxy_pass = "proxy_pass"
        self.engine.proxy_host = "proxy.example.com"
        self.engine.proxy_port = "3128"

        credentials = MagicMock()
        credentials.username = "username"
        credentials.password = "password"

        ms = mock_server.return_value
        self.engine.connect_to_rhn(credentials)
        mock_server.assert_called_with("https://some.host.example.com/rpc/api", proxy="proxy_user:proxy_pass@proxy.example.com:3128")
        ms.auth.login.assert_called_with("username", "password")

    def test_check_is_org_admin(self):
        sc = MagicMock()
        sc.user.listRoles.return_value = ["org_admin"]
        self.engine.check_is_org_admin(sc, None, "some_username")

    def test_check_is_org_admin_failure(self):
        sc = MagicMock()
        sc.user.listRoles.return_value = ["bogus_role"]
        try:
            self.engine.check_is_org_admin(sc, None, "some_username")
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_conflicting_channels(self):
        channels = ["jbappplatform-4.3.0-i386-server-5-rpm",
            "jbappplatform-5-i386-server-5-rpm",
            ]
        try:
            self.engine.check_for_conflicting_channels(channels)
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_no_conflicting_channels(self):
        channels = ["some-other-channel-i386-server-5-rpm",
            "jbappplatform-5-i386-server-5-rpm",
            ]
        self.engine.check_for_conflicting_channels(channels)

    @patch("__builtin__.open")
    def test_get_release(self, mock_open):
        mock_open.return_value = StringIO.StringIO("Red Hat Enterprise Linux Server release 6.3 (Santiago)")
        release = self.engine.get_release()
        self.assertEquals(release, "RHEL-6")

    @patch("__builtin__.open")
    def test_read_channel_cert_mapping(self, mock_open):
        mock_open.return_value.readlines.return_value = [
            "xyz: abc\n",
            "#some comment\n",
            ]
        data_dict = self.engine.read_channel_cert_mapping(None)
        self.assertEquals(data_dict, {"xyz": "abc"})

    def test_handle_collisions(self):
        cmap = {
                '1': {'cert-a-1.pem': ['chan1', 'chan2'], 'cert-b-1.pem': ['chan3']},
                '2': {'cert-x-2.pem': ['chan4', 'chan5']},
                '3': {'cert-m-3.pem': ['chanA'], 'cert-n-3.pem': ['chanB'], 'cert-o-3.pem': ['chanC']}
        }

        with Capture() as cap:
            try:
                self.engine.handle_collisions(cmap)
            except SystemExit, e:
                self.assertEquals(e.code, 1)
            else:
                self.fail("No exception raised")
            output = cap.out.strip()
            self.assertTrue(re.search("chan1\s*chan2\s*chan3", output))
            self.assertFalse(re.search("chan4", output))
            self.assertTrue(re.search("chanA\s*chanB", output))

    def test_accept_channels_mapping_to_same_cert(self):
        cmap = {'1': {'cert-a-1.pem': ['channel1', 'channel2']},
                '2': {'cert-x-2.pem': ['channel3']}
        }
        try:
            self.engine.handle_collisions(cmap)
        except SystemExit:
            self.fail("Exception raised unexpectedly")

    def test_detects_collisions(self):
        def stub_read_channel_cert_mapping(mappingfile):
            return {"a": "a-1.pem", "b": "b-1.pem"}

        def stub_get_release():
            return "RHEL-6"

        subscribed_channels = ["a", "b"]
        self.engine.read_channel_cert_mapping = stub_read_channel_cert_mapping
        self.engine.get_release = stub_get_release

        try:
            self.engine.deploy_prod_certificates(subscribed_channels)
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_require_force(self):
        def stub_read_channel_cert_mapping(mappingfile):
            return {"a": "a-1.pem", "b": "b-2.pem", "c": "none"}

        def stub_get_release():
            return "RHEL-6"

        subscribed_channels = ["a", "b", "c", "d"]
        self.engine.read_channel_cert_mapping = stub_read_channel_cert_mapping
        self.engine.get_release = stub_get_release
        self.engine.options = self.create_options(['force'])

        try:
            self.engine.deploy_prod_certificates(subscribed_channels)
        except SystemExit, e:
            self.assertEquals(e.code, 1)
        else:
            self.fail("No exception raised")

    @patch("shutil.copy2")
    def test_deploy_prod_certificates(self, mock_shutil):
        mock_product_directory = NonCallableMock(spec=ProductDirectory, path="/some/path")
        inj.provide(inj.PROD_DIR, mock_product_directory)

        mock_shutil.return_value = True
        self.engine.db = MagicMock()

        def stub_read_channel_cert_mapping(mappingfile):
            return {"a": "a-1.pem"}

        def stub_get_release():
            return "RHEL-6"

        subscribed_channels = ["a"]
        self.engine.read_channel_cert_mapping = stub_read_channel_cert_mapping
        self.engine.get_release = stub_get_release

        self.engine.deploy_prod_certificates(subscribed_channels)
        mock_shutil.assert_called_with("/usr/share/rhsm/product/RHEL-6/a-1.pem", "/some/path/1.pem")
        self.engine.db.add.assert_called_with("1", "a")
        self.engine.db.write.assert_called_with()

    @patch("os.path.isfile")
    @patch("os.remove")
    def test_clean_up_remove_68_pem(self, mock_remove, mock_isfile):
        mock_product_directory = NonCallableMock(spec=ProductDirectory)
        mock_product_directory.path = "/some/path"
        inj.provide(inj.PROD_DIR, mock_product_directory)
        self.engine.db = MagicMock()
        mock_isfile.side_effect = [True, True]
        self.engine.clean_up([])
        mock_remove.assert_called_with("/some/path/68.pem")
        self.engine.db.delete.assert_called_with("68")
        self.engine.db.write.assert_called_with()

    @patch("os.path.isfile")
    @patch("os.remove")
    def test_clean_up_remove_180_pem(self, mock_remove, mock_isfile):
        mock_product_directory = NonCallableMock(spec=ProductDirectory)
        mock_product_directory.path = "/some/path"
        inj.provide(inj.PROD_DIR, mock_product_directory)

        self.engine.db = MagicMock()
        mock_isfile.side_effect = [False, False]
        self.engine.clean_up([
            "rhel-i386-client-dts-5-beta",
            "rhel-i386-client-dts-5",
            ])
        mock_remove.assert_called_with("/some/path/180.pem")
        self.engine.db.delete.assert_called_with("180")
        self.engine.db.write.assert_called_with()

    def test_double_mapping_regex(self):
        regex = migrate.DOUBLE_MAPPED
        for channel in self.double_mapped_channels:
            self.assertTrue(re.match(regex, channel))

        for channel in self.single_mapped_channels:
            self.assertFalse(re.match(regex, channel))

    def test_single_mapping_regex(self):
        regex = migrate.SINGLE_MAPPED
        for channel in self.double_mapped_channels:
            self.assertFalse(re.match(regex, channel))

        for channel in self.single_mapped_channels:
            self.assertTrue(re.match(regex, channel))

    @patch("shutil.move")
    def test_unregister_from_rhn_exception(self, mock_shutil):
        rhn_config = {"systemIdPath": "/some/path"}
        self.engine.rhncfg = rhn_config
        sc = MagicMock()
        sc.system.deleteSystems.side_effect = Exception

        def stub_get_system_id():
            pass

        def stub_disable_yum_rhn_plugin():
            pass

        self.engine.get_system_id = stub_get_system_id
        self.engine.disable_yum_rhn_plugin = stub_disable_yum_rhn_plugin

        self.engine.unregister_system_from_rhn_classic(sc, None)
        mock_shutil.assert_called_with("/some/path", "/some/path.save")

    @patch("__builtin__.open")
    def test_disable_yum_rhn_plugin(self, mock_open):
        mo = mock_open.return_value
        mo.readlines.return_value = [
            "[channel]",
            "enabled = 1",
            "[main]",
            "enabled = 1",
            ]
        self.engine.disable_yum_rhn_plugin()

        expected = [call('[channel]'),
            call('enabled = 1'),
            call('[main]'),
            call('enabled = 0'),  # Note that enabled is now 0.
            ]
        self.assertTrue(mo.write.call_args_list == expected)

    @patch("os.remove")
    def test_unregister_from_rhn(self, mock_remove):
        rhn_config = {"systemIdPath": "/some/path"}
        self.engine.rhncfg = rhn_config
        sc = MagicMock()
        sc.system.deleteSystems.return_value = True

        def stub_get_system_id():
            pass

        def stub_disable_yum_rhn_plugin():
            pass

        self.engine.get_system_id = stub_get_system_id
        self.engine.disable_yum_rhn_plugin = stub_disable_yum_rhn_plugin

        self.engine.unregister_system_from_rhn_classic(sc, None)
        mock_remove.assert_called_with("/some/path")

    @patch("subprocess.call")
    def test_register_failure(self, mock_subprocess):
        self.engine.options = self.create_options({'serverurl': 'foobar'})

        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"

        mock_subprocess.return_value = 1
        try:
            self.engine.register(credentials, "", "")
        except SystemExit, e:
            self.assertEquals(e.code, 2)
        else:
            self.fail("No exception raised")

    @patch("subprocess.call")
    @patch.object(identity.ConsumerIdentity, "read")
    def test_register(self, mock_read, mock_subprocess):
        self.engine.options = self.create_options({'serverurl': 'foobar'})

        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"

        mock_subprocess.return_value = 0
        mock_read.return_value = MagicMock()
        self.engine.register(credentials, "org", "env")

        arg_list = ['subscription-manager',
            'register',
            '--serverurl=foobar',
            '--username=foo',
            '--password=bar',
            '--org=org',
            '--environment=env',
            ]

        mock_subprocess.assert_called_with(arg_list)

    def test_select_service_level(self):
        self.engine.cp.getServiceLevelList = MagicMock()
        self.engine.cp.getServiceLevelList.return_value = ["Premium", "Standard"]
        service_level = self.engine.select_service_level("my_org", "Premium")
        self.assertEquals(service_level, "Premium")

    @patch("subscription_manager.migrate.migrate.Menu")
    def test_select_service_level_with_menu(self, mock_menu):
        self.engine.cp.getServiceLevelList = MagicMock()
        self.engine.cp.getServiceLevelList.return_value = ["Premium", "Standard"]
        mock_menu.return_value.choose.return_value = "Premium"
        service_level = self.engine.select_service_level("my_org", "Something Else")
        self.assertEquals(service_level, "Premium")

    @patch("subprocess.call")
    @patch("os.getenv")
    @patch("os.path.exists")
    def test_subscribe(self, mock_exists, mock_getenv, mock_subprocess):
        self.engine.options = self.create_options({'gui': False})
        mock_getenv.return_value = True
        mock_exists.return_value = True

        mock_consumer = MagicMock()
        self.engine.subscribe(mock_consumer, "foobar")
        arg_list = [
            'subscription-manager',
            'subscribe',
            '--auto',
            '--servicelevel=foobar',
            ]
        mock_subprocess.assert_called_with(arg_list)

    @patch("subscription_manager.repolib.RepoActionInvoker")
    @patch("subscription_manager.repolib.RepoFile")
    def test_enable_extra_channels(self, mock_repofile, mock_repolib):
        mrf = mock_repofile.return_value
        subscribed_channels = [
            "rhel-i386-client-supplementary-5",
            "rhel-i386-client-optional-6",
            "rhel-i386-server-productivity-5",
            ]
        mrf.sections.return_value = [
            "supplementary",
            "optional-rpms",
            "productivity-rpms",
            ]
        self.engine.enable_extra_channels(subscribed_channels)
        expected = [call("supplementary", "enabled", "1"),
            call("optional-rpms", "enabled", "1"),
            call("productivity-rpms", "enabled", "1")]
        self.assertTrue(mrf.set.call_args_list == expected)
        mrf.write.assert_called_with()

    @patch("__builtin__.file")
    def test_get_system_id(self, mock_file):
        rhn_config = {
            "systemIdPath": "/tmp/foo",
            }
        mock_file.return_value.read.return_value = """
        <params>
          <param>
            <value>
              <struct>
                <member>
                  <name>system_id</name>
                  <value>
                    <string>ID-123</string>
                  </value>
                </member>
              </struct>
            </value>
          </param>
        </params>
        """
        self.engine.rhncfg = rhn_config
        system_id = self.engine.get_system_id()
        self.assertEquals(123, system_id)
