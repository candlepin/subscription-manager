from __future__ import print_function, division, absolute_import

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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import re
import six
from . import stubs

from mock import patch, NonCallableMock, MagicMock, Mock, call
from rhsm.https import ssl
from .fixture import Capture, SubManFixture, temp_file, OPEN_FUNCTION
from optparse import OptionParser
from textwrap import dedent

from nose import SkipTest

from subscription_manager import injection as inj
try:
    from subscription_manager.migrate import migrate
except ImportError:
    raise SkipTest("Couldn't import rhn modules for migration tests")

from subscription_manager.certdirectory import ProductDirectory


class TestMenu(unittest.TestCase):
    def setUp(self):
        self.menu = migrate.Menu([
            ("displayed-hello", "Hello"),
            ("displayed-world", "World"),
            ], "")

    def test_enter_negative(self):
        self.assertRaises(migrate.InvalidChoiceError, self.menu._get_item, -1)

    def test_enter_nonnumber(self):
        self.assertRaises(migrate.InvalidChoiceError, self.menu._get_item, "a")

    def test_get_item(self):
        self.assertEqual("Hello", self.menu._get_item(1))

    @patch("six.moves.input")
    @patch.object(migrate.Menu, "display_invalid")
    def test_choose(self, mock_display_invalid, mock_input):
        mock_input.side_effect = ["9000", "1"]
        choice = self.menu.choose()

        mock_display_invalid.assert_called_once_with()
        self.assertEqual(choice, "Hello")


class TestMigration(SubManFixture):
    def create_options(self, **kwargs):
        """
        Create a mock options object.  Send in a dictionary with the option destination and values
        and they will be set.  Note that you must use the destination and not just the option name.
        For example, if the option is --my-option, the destination (unless customized) will be
        my_option.
        """
        p = OptionParser()
        migrate.add_parser_options(p)

        # Set the list of acceptable attributes for this Mock.
        valid_options = [x for x in p.option_list if x.dest is not None]
        mock_opts = Mock(spec=[o.dest for o in valid_options])

        # Set everything to the default
        def set_default(opt):
            # Optparse uses a tuple to indicate if no default has been set.
            if opt.default != ("NO", "DEFAULT"):
                val = opt.default
            else:
                val = None
            setattr(mock_opts, opt.dest, val)

        for x in valid_options:
            set_default(x)

        if not kwargs:
            kwargs = {}

        for k, v in list(kwargs.items()):
            setattr(mock_opts, k, v)

        # The five_to_six option is set after argument parsing in the module so we set it
        # for convenience.
        if 'five_to_six' not in kwargs:
            mock_opts.five_to_six = False

        return mock_opts

    def setUp(self):
        super(TestMigration, self).setUp()
        migrate.initUp2dateConfig = lambda: {}

        self.system_id = dedent("""
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
        """)

        patch('subscription_manager.migrate.migrate.ProductDatabase').start()
        with temp_file(self.system_id) as temp_id_file:
            with patch("subscription_manager.migrate.migrate.initUp2dateConfig") as init_conf:
                init_conf.return_value = {"systemIdPath": temp_id_file}
                self.engine = migrate.MigrationEngine(self.create_options())
                self.engine.cp = stubs.StubUEP()
                self.system_id_file = temp_id_file

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

    def test_5to6_options(self):
        five_to_six = True
        parser = OptionParser()
        migrate.add_parser_options(parser, five_to_six)
        self.assertTrue(parser.has_option("--registration-state"))
        self.assertFalse(parser.has_option("--org"))
        self.assertFalse(parser.has_option("--environment"))
        self.assertFalse(parser.has_option("--force"))
        self.assertFalse(parser.has_option("--activation-key"))
        self.assertTrue(parser.has_option("--remove-rhn-packages"))
        (opts, args) = parser.parse_args([])
        migrate.set_defaults(opts, five_to_six)
        self.assertTrue(opts.five_to_six)
        self.assertEqual(None, opts.org)
        self.assertEqual(None, opts.environment)
        self.assertTrue(opts.force)

    def test_classic_migration_options(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        self.assertTrue(parser.has_option("--keep"))
        self.assertTrue(parser.has_option("--org"))
        self.assertTrue(parser.has_option("--environment"))
        self.assertTrue(parser.has_option("--force"))
        self.assertTrue(parser.has_option("--activation-key"))
        self.assertTrue(parser.has_option("--remove-rhn-packages"))
        (opts, args) = parser.parse_args([])
        migrate.set_defaults(opts, five_to_six_script=False)
        self.assertFalse(opts.five_to_six)
        self.assertEqual("purge", opts.registration_state)

    def test_choices_for_registration_state(self):
        parser = OptionParser()
        migrate.add_parser_options(parser, five_to_six_script=True)
        valid = ["keep", "unentitle", "purge"]
        for opt in valid:
            (options, args) = parser.parse_args(["--registration-state", opt])

        parser = OptionParser()
        migrate.add_parser_options(parser, five_to_six_script=False)
        (options, args) = parser.parse_args(["--keep"])
        self.assertEqual("keep", options.registration_state)

        (options, args) = parser.parse_args([""])
        self.assertEqual("purge", options.registration_state)

    def test_registration_state_default(self):
        parser = OptionParser()
        migrate.add_parser_options(parser, five_to_six_script=True)
        (options, args) = parser.parse_args([])
        self.assertEqual("unentitle", options.registration_state)

    def test_mutually_exclusive_auto_service_level_options(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        (options, args) = parser.parse_args(["--no-auto", "--servicelevel", "foo"])
        self.assertRaises(SystemExit, migrate.validate_options, (options))

    def test_mutually_exclusive_activation_keys_and_environment(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        (options, args) = parser.parse_args(["--environment", "foo", "--activation-key", "bar"])
        self.assertRaises(SystemExit, migrate.validate_options, (options))

    def test_activation_keys_require_org(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        (options, args) = parser.parse_args(["--activation-key", "bar"])
        self.assertRaises(SystemExit, migrate.validate_options, (options))

    def test_activation_key_forbids_destination_credentials(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        (options, args) = parser.parse_args(["--activation-key", "bar", "--destination-user", "x"])
        self.assertRaises(SystemExit, migrate.validate_options, (options))
        (options, args) = parser.parse_args(["--activation-key", "bar", "--destination-password", "y"])
        self.assertRaises(SystemExit, migrate.validate_options, (options))

    @patch.object(stubs.StubConfig, "get", autospec=True)
    def test_is_hosted(self, mock_get):
        mock_get.return_value = "subscription.rhsm.redhat.com"
        self.assertTrue(migrate.is_hosted())
        mock_get.return_value = "subscription.rhn.redhat.com"
        self.assertTrue(migrate.is_hosted())

    @patch.object(stubs.StubConfig, "get", autospec=True)
    def test_is_not_hosted(self, mock_get):
        mock_get.return_value = "subscription.example.com"
        self.assertFalse(migrate.is_hosted())

    @patch("six.moves.input")
    @patch("getpass.getpass", autospec=True)
    def test_authenticate(self, mock_getpass, mock_input):
        mock_input.return_value = "username"
        mock_getpass.return_value = "password"
        creds = self.engine.authenticate(None, None, "Some prompt", "Some other prompt")
        self.assertEqual(creds.username, "username")
        self.assertEqual(creds.password, "password")

    def test_authenticate_when_values_given(self):
        creds = self.engine.authenticate("username", "password", "Some prompt", "Some other prompt")
        self.assertEqual(creds.username, "username")
        self.assertEqual(creds.password, "password")

    @patch("six.moves.input")
    @patch("getpass.getpass", autospec=True)
    def test_get_auth_with_serverurl(self, mock_getpass, mock_input):
        self.engine.options = self.create_options(destination_url='foobar')

        mock_input.side_effect = iter(["legacy_username", "destination_username"])
        mock_getpass.side_effect = iter(["legacy_password", "destination_password"])

        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "destination_username")
        self.assertEqual(self.engine.destination_creds.password, "destination_password")

    @patch("six.moves.input")
    @patch("getpass.getpass", autospec=True)
    def test_get_auth_without_serverurl_and_not_hosted(self, mock_getpass, mock_input):
        self.engine.options = self.create_options()

        mock_input.side_effect = iter(["legacy_username", "destination_username"])
        mock_getpass.side_effect = iter(["legacy_password", "destination_password"])

        self.engine.is_hosted = False
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "destination_username")
        self.assertEqual(self.engine.destination_creds.password, "destination_password")

    @patch("six.moves.input")
    @patch("getpass.getpass", autospec=True)
    def test_get_auth_without_serverurl_and_is_hosted(self, mock_getpass, mock_input):
        self.engine.options = self.create_options()

        mock_input.return_value = "legacy_username"
        mock_getpass.return_value = "legacy_password"

        self.engine.is_hosted = True
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "legacy_username")
        self.assertEqual(self.engine.destination_creds.password, "legacy_password")

    def test_get_auth_with_provided_rhn_creds(self):
        self.engine.options = self.create_options(legacy_user='legacy_username', legacy_password='legacy_password')
        self.engine.is_hosted = True
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "legacy_username")
        self.assertEqual(self.engine.destination_creds.password, "legacy_password")

    @patch("getpass.getpass", autospec=True)
    def test_gets_password_when_only_username_give(self, mock_getpass):
        self.engine.options = self.create_options(legacy_user='legacy_username')

        mock_getpass.return_value = "legacy_password"
        self.engine.is_hosted = True
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "legacy_username")
        self.assertEqual(self.engine.destination_creds.password, "legacy_password")

    @patch("getpass.getpass", autospec=True)
    def test_gets_destination_password_when_only_destination_username_given(self, mock_getpass):
        self.engine.options = self.create_options(
            legacy_user='legacy_username',
            legacy_password='legacy_password',
            destination_user='destination_username')

        mock_getpass.return_value = "destination_password"
        self.engine.is_hosted = False
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "destination_username")
        self.assertEqual(self.engine.destination_creds.password, "destination_password")

    @patch("six.moves.input")
    @patch("getpass.getpass", autospec=True)
    def test_gets_destination_auth_in_keep_state(self, mock_getpass, mock_input):
        self.engine.options = self.create_options(
            registration_state='keep'
        )
        mock_input.return_value = "destination_username"
        mock_getpass.return_value = "destination_password"

        self.engine.is_hosted = False
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, None)
        self.assertEqual(self.engine.legacy_creds.password, None)
        self.assertEqual(self.engine.destination_creds.username, "destination_username")
        self.assertEqual(self.engine.destination_creds.password, "destination_password")

    def test_all_auth_provided(self):
        self.engine.options = self.create_options(
            legacy_user='legacy_username',
            legacy_password='legacy_password',
            destination_user='destination_username',
            destination_password='destination_password')

        self.engine.is_hosted = False
        self.engine.get_auth()
        self.assertEqual(self.engine.legacy_creds.username, "legacy_username")
        self.assertEqual(self.engine.legacy_creds.password, "legacy_password")
        self.assertEqual(self.engine.destination_creds.username, "destination_username")
        self.assertEqual(self.engine.destination_creds.password, "destination_password")

    def test_broken_proxy(self):
        rhn_config = {
            "enableProxy": True,
            "httpProxy": "bad_proxy",
        }
        self.engine.rhncfg = rhn_config
        try:
            self.engine.transfer_http_proxy_settings()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_CONFIG)
        else:
            self.fail("No exception raised")

    def test_setting_unauthenticated_proxy(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options(noproxy=False)

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "proxy.example.com:123",
            "enableProxyAuth": False,
            }
        self.engine.rhncfg = rhn_config
        section = MagicMock()
        self.engine.rhsmcfg.__getitem__.return_value = section

        self.engine.transfer_http_proxy_settings()
        expected = [call("proxy_hostname", "proxy.example.com"),
            call("proxy_port", "123"),
            call("proxy_user", ""),
            call("proxy_password", ""),
        ]
        self.assertTrue(section.__setitem__.call_args_list == expected)
        self.engine.rhsmcfg.persist.assert_called_once_with()

    def test_setting_authenticated_proxy(self):
        self.engine.rhsmcfg = MagicMock()
        section = MagicMock()
        self.engine.rhsmcfg.__getitem__.return_value = section

        self.engine.options = self.create_options(noproxy=False)

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "proxy.example.com:123",
            "enableProxyAuth": True,
            "proxyUser": "foo",
            "proxyPassword": "bar",
        }
        self.engine.rhncfg = rhn_config
        self.engine.transfer_http_proxy_settings()
        expected = [call("proxy_hostname", "proxy.example.com"),
            call("proxy_port", "123"),
            call("proxy_user", "foo"),
            call("proxy_password", "bar"),
        ]
        self.assertTrue(section.__setitem__.call_args_list == expected)
        self.engine.rhsmcfg.persist.assert_called_once_with()

    def test_setting_prefixed_proxy(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options(noproxy=False)

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "http://proxy.example.com:123",
            "enableProxyAuth": False,
            }
        self.engine.rhncfg = rhn_config
        section = MagicMock()
        self.engine.rhsmcfg.__getitem__.return_value = section
        self.engine.transfer_http_proxy_settings()
        expected = [
            call("proxy_hostname", "proxy.example.com"),
            call("proxy_port", "123"),
            call("proxy_user", ""),
            call("proxy_password", ""),
        ]
        self.assertTrue(section.__setitem__.call_args_list == expected)
        self.engine.rhsmcfg.persist.assert_called_once_with()

    def test_noproxy_option(self):
        self.engine.rhsmcfg = MagicMock()
        self.engine.options = self.create_options(noproxy=True)

        rhn_config = {
            "enableProxy": True,
            "httpProxy": "proxy.example.com:123",
            "enableProxyAuth": False,
            }
        self.engine.rhncfg = rhn_config
        section = MagicMock()
        self.engine.rhsmcfg.__getitem__.return_value = section
        self.engine.transfer_http_proxy_settings()
        expected = [call("proxy_hostname", ""),
            call("proxy_port", ""),
            call("proxy_user", ""),
            call("proxy_password", ""),
            ]
        self.assertTrue(section.__setitem__.call_args_list == expected)
        self.assertEqual("proxy.example.com", self.engine.proxy_host)
        self.assertEqual("123", self.engine.proxy_port)
        self.assertEqual(None, self.engine.proxy_user)
        self.assertEqual(None, self.engine.proxy_pass)

    @patch("rhn.rpclib.Server")
    def test_load_transition_data(self, mock_server):
        mock_server.system.transitionDataForSystem.return_value = {"uuid": "1"}
        self.engine.load_transition_data(mock_server)
        mock_server.system.transitionDataForSystem.assert_called_once_with(self.system_id)
        self.assertEqual("1", self.engine.consumer_id)

    @patch("rhn.rpclib.Server")
    def test_legacy_unentitle(self, mock_server):
        self.engine.disable_yum_rhn_plugin = MagicMock(return_value=True)
        self.engine.legacy_unentitle(mock_server)
        mock_server.system.unentitle.assert_called_once_with(self.system_id)

    @patch("rhn.rpclib.Server")
    def test_legacy_unentitle_fails_gracefully(self, mock_server):
        self.engine.disable_yum_rhn_plugin = MagicMock(side_effect=IOError)
        self.engine.legacy_unentitle(mock_server)
        mock_server.system.unentitle.assert_called_once_with(self.system_id)

    @patch("rhn.rpclib.Server")
    @patch("subscription_manager.migrate.migrate.getChannels")
    def test_get_subscribed_channels_list(self, mock_channels, mock_server):
        self.engine.options = self.create_options()
        key = "key"
        mock_channels.return_value.channels.return_value = [
            {"label": "foo"},
            {"label": "bar"},
            ]
        results = self.engine.get_subscribed_channels_list(mock_server, key)
        self.assertEqual(["foo", "bar"], results)

    @patch("subscription_manager.migrate.migrate.getChannels")
    def test_get_subscribed_channels_list_5to6(self, mock_channels):
        self.engine.options = self.create_options(five_to_six=True)
        server = "server"
        key = "key"
        channel_list = [
            {"label": "foo"},
            {"label": "bar"},
            ]
        mock_channels.return_value.channels.return_value = channel_list
        self.engine.resolve_base_channel = Mock(side_effect=channel_list)

        results = self.engine.get_subscribed_channels_list(server, key)
        self.assertEqual(["foo", "bar"], results)
        calls = [call.resolve_base_channel("foo", server, key), call.resolve_base_channel("bar", server, key)]
        self.engine.resolve_base_channel.assert_has_calls(calls, any_order=True)

    def test_consumer_exists(self):
        self.engine.cp.getConsumer = MagicMock(return_value=1)
        exists = self.engine.consumer_exists("123")
        self.assertTrue(exists)
        self.engine.cp.getConsumer.assert_called_once_with("123")

    def test_consumer_does_not_exist(self):
        self.engine.cp.getConsumer = MagicMock(side_effect=ValueError)
        exists = self.engine.consumer_exists("123")
        self.assertFalse(exists)
        self.engine.cp.getConsumer.assert_called_once_with("123")

    def test_no_server_url_provided_basic_auth(self):
        self.engine.options = self.create_options()

        self.engine.rhsmcfg = MagicMock()
        section = MagicMock()
        self.engine.rhsmcfg.__getitem__.return_value = section

        section.__getitem__.return_value = MagicMock(side_effect=[
            "candlepin.example.com",
            "/candlepin",
        ])
        section.get_int = MagicMock(side_effect=[443])

        expected = [call("hostname"),
            call("prefix"),
        ]

        int_expected = [call("port")]

        self.engine.get_candlepin_connection("some_username", "some_password")
        self.assertTrue(section.__getitem__.call_args_list == expected)
        self.assertTrue(section.get_int.call_args_list == int_expected)

    def test_bad_server_url_basic_auth(self):
        self.engine.options = self.create_options(destination_url='http://')
        self.assertRaises(SystemExit,
                self.engine.get_candlepin_connection,
                "some_username",
                "some_password")

    def test_no_auth_connection_returned(self):
        conn = self.engine.get_candlepin_connection(None, None)
        self.assertEqual(None, conn.username)
        self.assertEqual(None, conn.password)

    # default injected identity is "valid"
    def test_already_registered_to_rhsm(self):
        self._inject_mock_valid_consumer()
        self.engine.options = self.create_options(
            five_to_six=False
        )
        with Capture() as c:
            self.assertRaises(SystemExit, self.engine.check_ok_to_proceed)
            self.assertTrue("Red Hat Subscription Management" in c.err)
            self.assertTrue("access.redhat.com" in c.err)

    def test_already_registered_to_sat_6(self):
        self._inject_mock_valid_consumer()
        self.engine.options = self.create_options(
            five_to_six=True
        )
        with Capture() as c:
            self.assertRaises(SystemExit, self.engine.check_ok_to_proceed)
            self.assertTrue("Satellite 6" in c.err)

    def test_ssl_error(self):
        self._inject_mock_invalid_consumer()
        self.engine.cp.getStatus = MagicMock(side_effect=ssl.SSLError)
        try:
            self.engine.check_ok_to_proceed()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)
        else:
            self.fail("No exception raised")

    def test_no_orgs(self):
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = []
        try:
            self.engine.get_org("some_username")
        except SystemExit as e:
            self.assertEqual(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_one_org(self):
        self.engine.options = self.create_options()
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [{"key": "my_org", "displayName": "My Org"}]
        org = self.engine.get_org("some_username")
        self.assertEqual(org, "my_org")

    @patch("six.moves.input")
    def test_enter_org_key(self, mock_input):
        self.engine.options = self.create_options()
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        mock_input.return_value = "my_org"
        org = self.engine.get_org("some_username")
        self.assertEqual(org, "my_org")

    @patch("six.moves.input")
    def test_enter_org_name(self, mock_input):
        self.engine.options = self.create_options()
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        mock_input.return_value = "My Org"
        org = self.engine.get_org("some_username")
        self.assertEqual(org, "my_org")

    @patch("six.moves.input")
    def test_enter_bad_org(self, mock_input):
        self.engine.options = self.create_options()
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        mock_input.return_value = "Some other org"
        try:
            self.engine.get_org("some_username")
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_DATAERR)
        else:
            self.fail("No exception raised")

    def test_org_option(self):
        self.engine.options = self.create_options(org='my_org')
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        org = self.engine.get_org("some_username")
        self.assertEqual(org, "my_org")

    def test_bad_org_option(self):
        self.engine.options = self.create_options(org='nonsense')
        self.engine.cp.getOwnerList = MagicMock()
        self.engine.cp.getOwnerList.return_value = [
            {"key": "my_org", "displayName": "My Org"},
            {"key": "second_org", "displayName": "Second Org"},
            ]
        try:
            self.engine.get_org("some_username")
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_DATAERR)
        else:
            self.fail("No exception raised")

    def test_environment_supported_exception(self):
        self.engine.cp.supports_resource = MagicMock(side_effect=Exception)
        try:
            self.engine.get_environment("some_org")
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)
        else:
            self.fail("No exception raised")

    def test_environment_with_no_resource(self):
        self.engine.options = self.create_options()
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = False
        env = self.engine.get_environment("some_org")
        self.assertEqual(env, None)

    def test_single_environment_requires_no_input(self):
        self.engine.options = self.create_options()
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"}
            ]

        env = self.engine.get_environment("some_org")
        self.assertEqual(env, "My Environment")

    @patch("six.moves.input")
    def test_enter_environment_name(self, mock_input):
        self.engine.options = self.create_options()
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment"},
            {"name": "Another Environment"},
            ]

        mock_input.return_value = "My Environment"
        env = self.engine.get_environment("some_org")
        self.assertEqual(env, "My Environment")

    @patch("six.moves.input")
    def test_enter_environment_label(self, mock_input):
        self.engine.options = self.create_options()
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]

        mock_input.return_value = "my_environment"
        env = self.engine.get_environment("some_org")
        self.assertEqual(env, "My Environment")

    @patch("six.moves.input")
    def test_enter_environment_displayName(self, mock_input):
        self.engine.options = self.create_options()
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True

        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "displayName": "my_environment"},
            {"name": "Another Environment", "displayName": "another_environment"},
            ]

        mock_input.return_value = "my_environment"
        env = self.engine.get_environment("some_org")
        self.assertEqual(env, "My Environment")

    @patch("six.moves.input")
    def test_enter_bad_environment(self, mock_input):
        self.engine.options = self.create_options()
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
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_DATAERR)
        else:
            self.fail("No exception raised")

    def test_environment_option(self):
        self.engine.options = self.create_options(environment='My Environment')
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True
        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]

        env = self.engine.get_environment("some_org")
        self.assertEqual(env, "My Environment")

    def test_bad_environment_option(self):
        self.engine.options = self.create_options(environment='nonsense')
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = True
        self.engine.cp.getEnvironmentList = MagicMock()
        self.engine.cp.getEnvironmentList.return_value = [
            {"name": "My Environment", "label": "my_environment"},
            {"name": "Another Environment", "label": "another_environment"},
            ]
        try:
            self.engine.get_environment("some_org")
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_DATAERR)
        else:
            self.fail("No exception raised")

    def test_environment_option_with_no_resource(self):
        self.engine.options = self.create_options(environment='My Environment')
        self.engine.cp.supports_resource = MagicMock()
        self.engine.cp.supports_resource.return_value = False
        try:
            self.engine.get_environment("some_org")
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_UNAVAILABLE)
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

    def test_check_has_access(self):
        sc = MagicMock()
        sc.system.getDetails.return_value = True
        self.engine.check_has_access(sc, "key")

    def test_check_has_access_failure(self):
        sc = MagicMock()
        sc.system.getDetails.side_effect = NameError
        self.assertRaises(SystemExit, self.engine.check_has_access, sc, Mock(name="fake key"))
        self.assertEqual(1, len(sc.system.getDetails.mock_calls))

    def test_check_has_access_fails_with_no_key(self):
        self.assertRaises(SystemExit, self.engine.check_has_access, Mock(name="fake session"), None)

    def test_conflicting_channels(self):
        channels = ["jbappplatform-4.3.0-i386-server-5-rpm",
            "jbappplatform-5-i386-server-5-rpm",
            ]
        try:
            self.engine.check_for_conflicting_channels(channels)
        except SystemExit as e:
            self.assertEqual(e.code, 1)
        else:
            self.fail("No exception raised")

    def test_base_channel_resolution(self):
        channel_chain = [
                {'clone_original': 'c', 'label': 'd'},
                {'clone_original': 'b', 'label': 'c'},
                {'clone_original': 'a', 'label': 'b'},
                {'clone_original': '', 'label': 'a'}
        ]
        mock_sc = Mock()
        mock_sc.channel.software.getDetails.side_effect = channel_chain
        chan = self.engine.resolve_base_channel('d', mock_sc, 'sk')
        self.assertEqual('a', chan['label'])

    def test_no_conflicting_channels(self):
        channels = ["some-other-channel-i386-server-5-rpm",
            "jbappplatform-5-i386-server-5-rpm",
            ]
        self.engine.check_for_conflicting_channels(channels)

    @patch(OPEN_FUNCTION, autospec=True)
    def test_get_release(self, mock_open):
        mock_open.return_value = six.StringIO("Red Hat Enterprise Linux Server release 6.3 (Santiago)")
        release = self.engine.get_release()
        self.assertEqual(release, "RHEL-6")

    @patch(OPEN_FUNCTION, autospec=True)
    def test_read_channel_cert_mapping(self, mock_open):
        mock_open.return_value.readlines.return_value = [
            "xyz: abc\n",
            "#some comment\n",
            ]
        data_dict = self.engine.read_channel_cert_mapping(None)
        self.assertEqual(data_dict, {"xyz": "abc"})

    def test_handle_collisions(self):
        cmap = {
                '1': {'cert-a-1.pem': ['chan1', 'chan2'], 'cert-b-1.pem': ['chan3']},
                '2': {'cert-x-2.pem': ['chan4', 'chan5']},
                '3': {'cert-m-3.pem': ['chanA'], 'cert-n-3.pem': ['chanB'], 'cert-o-3.pem': ['chanC']}
        }

        with Capture() as cap:
            try:
                self.engine.handle_collisions(cmap)
            except SystemExit as e:
                self.assertEqual(e.code, 1)
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
        except SystemExit as e:
            self.assertEqual(e.code, 1)
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
        self.engine.options = self.create_options()

        try:
            self.engine.deploy_prod_certificates(subscribed_channels)
        except SystemExit as e:
            self.assertEqual(e.code, 1)
        else:
            self.fail("No exception raised")

    @patch("shutil.copy2", autospec=True)
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

    @patch("os.path.isfile", autospec=True)
    @patch("os.remove", autospec=True)
    def test_clean_up_remove_68_pem(self, mock_remove, mock_isfile):
        mock_product_directory = NonCallableMock(spec=ProductDirectory)
        mock_product_directory.path = "/some/path"
        inj.provide(inj.PROD_DIR, mock_product_directory)
        self.engine.db = MagicMock()
        mock_isfile.side_effect = iter([True, True])
        self.engine.clean_up([])
        mock_remove.assert_called_with("/some/path/68.pem")
        self.engine.db.delete.assert_called_with("68")
        self.engine.db.write.assert_called_with()

    @patch("os.path.isfile", autospec=True)
    @patch("os.remove", autospec=True)
    def test_clean_up_remove_180_pem(self, mock_remove, mock_isfile):
        mock_product_directory = NonCallableMock(spec=ProductDirectory)
        mock_product_directory.path = "/some/path"
        inj.provide(inj.PROD_DIR, mock_product_directory)

        self.engine.db = MagicMock()
        mock_isfile.side_effect = iter([False, False])
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

    @patch("shutil.move", autospec=True)
    def test_unregister_from_rhn_exception(self, mock_shutil):
        sc = MagicMock()
        sc.system.deleteSystems.side_effect = Exception

        def stub_disable_yum_rhn_plugin():
            pass

        self.engine.disable_yum_rhn_plugin = stub_disable_yum_rhn_plugin

        self.engine.legacy_purge(sc, None)
        mock_shutil.assert_called_with(self.system_id_file, "%s.save" % self.system_id_file)

    @patch(OPEN_FUNCTION, autospec=True)
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

    @patch("os.remove", autospec=True)
    def test_unregister_from_rhn(self, mock_remove):
        sc = MagicMock()
        sc.system.deleteSystems.return_value = True

        def stub_disable_yum_rhn_plugin():
            pass

        self.engine.disable_yum_rhn_plugin = stub_disable_yum_rhn_plugin

        self.engine.legacy_purge(sc, None)
        mock_remove.assert_called_with(self.system_id_file)

    @patch("subprocess.call", autospec=True)
    def test_register_failure(self, mock_subprocess):
        self.engine.options = self.create_options(destination_url='foobar')

        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"

        self._inject_mock_invalid_consumer()
        try:
            self.engine.register(credentials, "", "")
        except SystemExit as e:
            self.assertEqual(e.code, 2)
        else:
            self.fail("No exception raised")

    @patch("subprocess.call", autospec=True)
    def test_register_5to6(self, mock_subprocess):
        self.engine.options = self.create_options(
            five_to_six=True,
            destination_url="http://example.com",
            service_level="x")
        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"
        self.engine.consumer_id = "id"

        self.engine.consumer_exists = MagicMock(return_value=True)
        self.engine.select_service_level = MagicMock(return_value="y")

        mock_subprocess.return_value = 0
        self._inject_mock_valid_consumer()
        self.engine.register(credentials, "org", "env")

        arg_list = ['subscription-manager',
            'register',
            '--username=foo',
            '--password=bar',
            '--environment=env',
            '--auto-attach',
            '--serverurl=http://example.com',
            '--org=org',
            '--consumerid=id',
            '--servicelevel=y',
            ]

        self.engine.consumer_exists.assert_called_once_with(self.engine.consumer_id)
        self.engine.select_service_level.assert_called_once_with("org", "x")
        mock_subprocess.assert_called_once_with(arg_list)

    @patch("subprocess.call", autospec=True)
    def test_register_no_auto(self, mock_subprocess):
        self.engine.options = self.create_options(auto=False)
        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"
        self.engine.consumer_id = "id"

        mock_subprocess.return_value = 0
        self._inject_mock_valid_consumer()
        self.engine.register(credentials, "org", "env")

        arg_list = ['subscription-manager',
            'register',
            '--username=foo',
            '--password=bar',
            '--environment=env',
            '--org=org',
            ]

        mock_subprocess.assert_called_once_with(arg_list)

    @patch("subprocess.call", autospec=True)
    def test_register_with_activation_keys(self, mock_subprocess):
        self.engine.options = self.create_options(destination_url='foobar', activation_keys=['hello', 'world'])

        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"

        mock_subprocess.return_value = 0
        self._inject_mock_valid_consumer()
        self.engine.register(credentials, "org", "env")

        arg_list = ['subscription-manager',
            'register',
            '--activationkey=hello',
            '--activationkey=world',
            '--serverurl=foobar',
            '--org=org',
            ]

        mock_subprocess.assert_called_with(arg_list)

    @patch("subprocess.call", autospec=True)
    def test_register(self, mock_subprocess):
        self.engine.options = self.create_options(destination_url='foobar')

        credentials = MagicMock()
        credentials.username = "foo"
        credentials.password = "bar"

        mock_subprocess.return_value = 0
        self._inject_mock_valid_consumer()
        self.engine.register(credentials, "org", "env")

        arg_list = ['subscription-manager',
            'register',
            '--username=foo',
            '--password=bar',
            '--environment=env',
            '--auto-attach',
            '--serverurl=foobar',
            '--org=org',
            ]

        mock_subprocess.assert_called_with(arg_list)

    def test_select_service_level(self):
        self.engine.cp.getServiceLevelList = MagicMock()
        self.engine.cp.getServiceLevelList.return_value = ["Premium", "Standard"]
        service_level = self.engine.select_service_level("my_org", "Premium")
        self.assertEqual(service_level, "Premium")

    @patch("subscription_manager.migrate.migrate.Menu")
    def test_select_service_level_with_menu(self, mock_menu):
        self.engine.cp.getServiceLevelList = MagicMock()
        self.engine.cp.getServiceLevelList.return_value = ["Premium", "Standard"]
        mock_menu.return_value.choose.return_value = "Premium"
        service_level = self.engine.select_service_level("my_org", "Something Else")
        self.assertEqual(service_level, "Premium")

    @patch("subscription_manager.repolib.RepoActionInvoker")
    @patch("subscription_manager.repolib.YumRepoFile")
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

    def test_get_system_id(self):
        mock_id = """
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
        system_id = self.engine.get_system_id(mock_id)
        self.assertEqual(123, system_id)

    def test_remove_rhn_packages_option_default(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        (opts, args) = parser.parse_args([])
        self.assertFalse(opts.remove_legacy_packages)

    def test_remove_rhn_packages_option(self):
        parser = OptionParser()
        migrate.add_parser_options(parser)
        (opts, args) = parser.parse_args(["--remove-rhn-packages"])
        self.assertTrue(opts.remove_legacy_packages)

    @patch(OPEN_FUNCTION, autospec=True)
    def test_is_using_systemd_false_on_rhel6(self, mock_open):
        mock_open.return_value = six.StringIO("Red Hat Enterprise Linux Server release 6.3 (Santiago)")
        self.assertFalse(self.engine.is_using_systemd())

    @patch(OPEN_FUNCTION, autospec=True)
    def test_is_using_systemd_true_on_rhel7(self, mock_open):
        mock_open.return_value = six.StringIO("Red Hat Enterprise Linux Server release 7.2 (Maipo)")
        self.assertTrue(self.engine.is_using_systemd())

    @patch("subprocess.call", autospec=True)
    def test_handle_legacy_daemons_systemd(self, mock_subprocess):
        self.engine.handle_legacy_daemons(using_systemd=True)
        self.assertIn('systemctl', mock_subprocess.call_args[0][0])

    @patch("subprocess.call", autospec=True)
    def test_handle_legacy_daemons_systemv(self, mock_subprocess):
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            self.engine.handle_legacy_daemons(using_systemd=False)
        self.assertIn('service', mock_subprocess.call_args[0][0])

    @patch("subprocess.call", autospec=True)
    def test_remove_rhn_packages(self, mock_subprocess):
        self.engine.remove_legacy_packages()

        self.assertIn('yum', mock_subprocess.call_args[0][0])
