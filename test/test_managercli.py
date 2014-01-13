# -*- coding: utf-8 -*-
import unittest
import re
import sys
import socket

# for monkey patching config
import stubs

from subscription_manager import managercli, managerlib
from subscription_manager.printing_utils import format_name, columnize, \
        _echo, _none_wrap
from subscription_manager.repolib import Repo
from stubs import MockStderr, StubEntitlementCertificate, \
        StubConsumerIdentity, StubProduct, StubUEP
from fixture import FakeException, FakeLogger, SubManFixture, \
        Capture, Matcher

import mock
from mock import patch
from mock import Mock
# for some exceptions
from rhsm import connection
from M2Crypto import SSL
from subscription_manager.overrides import Override

# FIXME: temp fix till we merge test fixture merged
# Note: we don't tear this patch down, everything needs it mocked,
# and we don't actually test this method
is_valid_server_patcher = mock.patch("subscription_manager.managercli.is_valid_server_info")
is_valid_server_mock = is_valid_server_patcher.start()
is_valid_server_mock.return_value = True


class TestCli(SubManFixture):
    # shut up stdout spew
    def setUp(self):
        SubManFixture.setUp(self)
        sys.stderr = stubs.MockStderr()

    def tearDown(self):
        sys.stderr = sys.__stderr__

    def test_cli(self):
        cli = managercli.ManagerCLI()
        self.assertTrue('register' in cli.cli_commands)

    @patch.object(managerlib, "check_identity_cert_perms")
    def test_main_checks_identity_cert_perms(self, check_identity_cert_perms_mock):
        cli = managercli.ManagerCLI()
        # Catch the expected SystemExit so that the test can continue.
        self.assertRaises(SystemExit, cli.main)
        check_identity_cert_perms_mock.assert_called_with()

    def test_main_empty(self):
        cli = managercli.ManagerCLI()
        self.assertRaises(SystemExit, cli.main)

    def test_cli_find_best_match(self):
        cli = managercli.ManagerCLI()
        best_match = cli._find_best_match(['subscription-manager', 'version'])
        self.assertEquals(best_match.name, 'version')

    # shouldn't match on -sdf names
    def test_cli_find_best_match_no_dash(self):
        cli = managercli.ManagerCLI()
        best_match = cli._find_best_match(['subscription-manager', '--version'])
        self.assertEquals(best_match, None)


class TestCliCommand(SubManFixture):
    command_class = managercli.CliCommand

    def setUp(self):
        super(TestCliCommand, self).setUp()
        self.cc = self.command_class()
        # neuter the _do_command, since this is mostly
        # for testing arg parsing
        self._orig_do_command = self.cc._do_command
        self.cc._do_command = self._do_command
#        self.cc.assert_should_be_registered = self._asert_should_be_registered

        self.mock_stdout = MockStderr()
        self.mock_stderr = MockStderr()
        sys.stderr = self.mock_stderr

    def tearDown(self):
        sys.stderr = sys.__stderr__

    def _do_command(self):
        pass

    def test_main_no_args(self):
        try:
            # we fall back to sys.argv if there
            # is no args passed in, so stub out
            # sys.argv for test
            sys.argv = ["subscription-manager"]
            self.cc.main()
        except SystemExit, e:
            # 2 == no args given
            self.assertEquals(e.code, 2)

    def test_main_empty_args(self):
        try:
            sys.argv = ["subscription-manager"]
            self.cc.main([])
        except SystemExit, e:
            # 2 == no args given
            self.assertEquals(e.code, 2)

    def _main_help(self, args):
        with Capture() as cap:
            try:
                self.cc.main(args)
            except SystemExit, e:
                # --help/-h returns 0
                self.assertEquals(e.code, 0)
        output = cap.out.strip()
        # I could test for strings here, but that
        # would break if we run tests in a locale/lang
        self.assertTrue(len(output) > 0)

    def test_main_short_help(self):
        self._main_help(["-h"])

    def test_main_long_help(self):
        self._main_help(["--help"])


# for command classes that expect proxy related cli args
class TestCliProxyCommand(TestCliCommand):
    def test_main_proxy_url(self):
        proxy_host = "example.com"
        proxy_port = "3128"
        proxy_url = "%s:%s" % (proxy_host, proxy_port)
        self.cc.main(["--proxy", proxy_url])
        self.assertEquals(proxy_url, self.cc.options.proxy_url)
        self.assertEquals(type(proxy_url), type(self.cc.options.proxy_url))
        self.assertEquals(proxy_host, self.cc.proxy_hostname)
        self.assertEquals(int(proxy_port), self.cc.proxy_port)

    def test_main_proxy_user(self):
        proxy_user = "buster"
        self.cc.main(["--proxyuser", proxy_user])
        self.assertEquals(proxy_user, self.cc.proxy_user)

    def test_main_proxy_password(self):
        proxy_password = "nomoresecrets"
        self.cc.main(["--proxypassword", proxy_password])
        self.assertEquals(proxy_password, self.cc.proxy_password)


class TestCleanCommand(TestCliCommand):
    command_class = managercli.CleanCommand


class TestRefreshCommand(TestCliProxyCommand):
    command_class = managercli.RefreshCommand


class TestIdentityCommand(TestCliProxyCommand):

    command_class = managercli.IdentityCommand

    def test_regenerate_no_force(self):
        self.cc.main(["--regenerate"])


# re, orgs
class TestOwnersCommand(TestCliProxyCommand):
    command_class = managercli.OwnersCommand

    def test_main_server_url(self):
        server_url = "https://subscription.rhn.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])


class TestEnvironmentsCommand(TestCliProxyCommand):
    command_class = managercli.EnvironmentsCommand

    def test_main_server_url(self):
        server_url = "https://subscription.rhn.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])

    def test_library_no_longer_filtered(self):
        self.cc.cp = StubUEP()
        environments = []
        environments.append({'name': 'JarJar'})
        environments.append({'name': 'Library'})
        environments.append({'name': 'library'})
        environments.append({'name': 'Binks'})
        self.cc.cp.setEnvironmentList(environments)
        results = self.cc._get_enviornments("Anikan")
        self.assertTrue(len(results) == 4)


class TestRegisterCommand(TestCliProxyCommand):
    command_class = managercli.RegisterCommand

    def setUp(self):
        super(TestRegisterCommand, self).setUp()
        self._inject_mock_invalid_consumer()
        # TODO: two versions of this, one registered, one not registered

    def _test_exception(self, args):
        try:
            self.cc.main(args)
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, -1)
        else:
            self.fail("No Exception Raised")

    def _test_no_exception(self, args):
        try:
            self.cc.main(args)
            self.cc._validate_options()
        except SystemExit:
            self.fail("Exception Raised")

    def test_keys_and_consumerid(self):
        self._test_exception(["--consumerid", "22", "--activationkey", "key"])

    def test_key_and_org(self):
        self._test_no_exception(["--activationkey", "key", "--org", "org"])

    def test_key_and_no_org(self):
        self._test_exception(["--activationkey", "key"])

    def test_empty_string_key_and_org(self):
        self._test_exception(["--activationkey=", "--org", "org"])

    def test_keys_and_username(self):
        self._test_exception(["--username", "bob", "--activationkey", "key"])

    def test_keys_and_environments(self):
        self._test_exception(["--environment", "JarJar", "--activationkey", "Binks"])

    def test_env_and_org(self):
        self._test_no_exception(["--env", "env", "--org", "org"])

    def test_no_commands(self):
        self._test_no_exception([])

    @patch.object(managercli.cfg, "save")
    def test_main_server_url(self, mock_save):
        server_url = "https://subscription.rhn.redhat.com/subscription"
        self._test_no_exception(["--serverurl", server_url])
        mock_save.assert_called_with()

    @patch.object(managercli.cfg, "save")
    def test_main_base_url(self, mock_save):
        base_url = "https://cdn.redhat.com"
        self._test_no_exception(["--baseurl", base_url])
        mock_save.assert_called_with()

    @patch.object(managercli.cfg, "save")
    def test_insecure(self, mock_save):
        self._test_no_exception(["--insecure"])
        mock_save.assert_called_with()


class TestListCommand(TestCliProxyCommand):
    command_class = managercli.ListCommand

    def setUp(self):
        self.indent = 1
        self.max_length = 40
        self.cert_with_service_level = StubEntitlementCertificate(
            StubProduct("test-product"), service_level="Premium")
        TestCliProxyCommand.setUp(self)

    @mock.patch('subscription_manager.managerlib.get_available_entitlements')
    def test_none_wrap_available_pool_id(self, mget_ents):
        list_command = managercli.ListCommand()

        def create_pool_list(*args, **kwargs):
            return [{'productName': 'dummy-name',
                     'productId': 'dummy-id',
                     'providedProducts': [],
                     'id': '888888888888',
                     'attributes': [{'name': 'is_virt_only',
                                     'value': 'false'}],
                     'pool_type': 'Some Type',
                     'quantity': '4',
                     'service_level': '',
                     'service_type': '',
                     'contractNumber': '5',
                     'multi-entitlement': 'false',
                     'endDate': '',
                     'suggested': '2'}]
        mget_ents.return_value = create_pool_list()

        with Capture() as cap:
            list_command.main(['list', '--available'])
        self.assertTrue('888888888888' in cap.out)

    def test_print_consumed_no_ents(self):
        try:
            self.cc.print_consumed()
            self.fail("Should have exited.")
        except SystemExit:
            pass

    def test_print_consumed_one_ent_one_product(self):
        product = StubProduct("product1")
        self.ent_dir.certs.append(StubEntitlementCertificate(product))
        self.cc.sorter = Mock()
        self.cc.sorter.get_subscription_reasons_map = Mock()
        self.cc.sorter.get_subscription_reasons_map.return_value = {}
        self.cc.print_consumed()

    def test_print_consumed_one_ent_no_product(self):
        self.ent_dir.certs.append(StubEntitlementCertificate(
            product=None))
        self.cc.sorter = Mock()
        self.cc.sorter.get_subscription_reasons_map = Mock()
        self.cc.sorter.get_subscription_reasons_map.return_value = {}
        self.cc.print_consumed()

    def test_print_consumed_prints_nothing_with_no_service_level_match(self):
        self.ent_dir.certs.append(self.cert_with_service_level)
        try:
            self.cc.print_consumed(service_level="NotFound")
            self.fail("Should have exited since an entitlement with the " +
                      "specified service level does not exist.")
        except SystemExit:
            pass

    def test_print_consumed_prints_enitlement_with_service_level_match(self):
        self.ent_dir.certs.append(self.cert_with_service_level)
        self.cc.sorter = Mock()
        self.cc.sorter.get_subscription_reasons_map = Mock()
        self.cc.sorter.get_subscription_reasons_map.return_value = {}
        self.cc.print_consumed(service_level="Premium")

    def test_filter_only_specified_service_level(self):
        pools = [{'service_level': 'Level1'},
                 {'service_level': 'Level2'},
                 {'service_level': 'Level3'}]
        filtered = self.cc._filter_pool_json_by_service_level(pools, "Level2")
        self.assertEqual(1, len(filtered))
        self.assertEqual("Level2", filtered[0]['service_level'])

    def test_no_pool_with_specified_filter(self):
        pools = [{'service_level': 'Level1'}]
        filtered = self.cc._filter_pool_json_by_service_level(pools, "NotFound")
        self.assertEqual(0, len(filtered))


class TestUnRegisterCommand(TestCliProxyCommand):
    command_class = managercli.UnRegisterCommand


class TestRedeemCommand(TestCliProxyCommand):
    command_class = managercli.RedeemCommand


class TestReposCommand(TestCliCommand):
    command_class = managercli.ReposCommand

    def setUp(self):
        super(TestReposCommand, self).setUp()
        self.cc.cp = Mock()

    def test_list(self):
        self.cc.main(["--list"])
        self.cc._validate_options()

    def test_enable(self):
        self.cc.main(["--enable", "one", "--enable", "two"])
        self.cc._validate_options()

    def test_disable(self):
        self.cc.main(["--disable", "one", "--disable", "two"])
        self.cc._validate_options()

    @mock.patch("subscription_manager.managercli.RepoLib")
    def test_set_repo_status(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('x'), Repo('y'), Repo('z')]
        items = ['x', 'y']
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items, False)

        expected_overrides = [{'contentLabel': i, 'name': 'enabled', 'value':
            '0'} for i in items]

        # The list of overrides sent to setContentOverrides is really a set of
        # dictionaries (since we don't know the order of the overrides).
        # However, since the dict class is not hashable, we cssert_items_equalsan't actually use
        # a set.  So we need a custom matcher to make sure that the
        # JSON passed in to setContentOverrides is what we expect.
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        repolib_instance.update.assert_called()

    @mock.patch("subscription_manager.managercli.RepoLib")
    def test_set_repo_status_with_wildcards(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = ['z*']
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items, False)

        expected_overrides = [{'contentLabel': i.id, 'name': 'enabled', 'value':
            '0'} for i in repos]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        repolib_instance.update.assert_called()

    @mock.patch("subscription_manager.managercli.RepoFile")
    def test_set_repo_status_when_disconnected(self, mock_repofile):
        self._inject_mock_invalid_consumer()
        mock_repofile_inst = mock_repofile.return_value

        enabled = {'enabled': '1'}.items()
        disabled = {'enabled': '0'}.items()

        zoo = Repo('zoo', enabled)
        zebra = Repo('zebra', disabled)
        zippy = Repo('zippy', enabled)
        zero = Repo('zero', disabled)
        repos = [zoo, zebra, zippy, zero]
        items = ['z*']

        self.cc._set_repo_status(repos, None, items, False)
        calls = [mock.call(r) for r in repos if r['enabled'] == 1]
        mock_repofile_inst.update.assert_has_calls(calls)
        for r in repos:
            self.assertEquals('0', r['enabled'])
        mock_repofile_inst.write.assert_called_once_with()


class TestConfigCommand(TestCliCommand):
    command_class = managercli.ConfigCommand

    def test_list(self):
        self.cc.main(["--list"])
        self.cc._validate_options()

    def test_remove(self):
        self.cc.main(["--remove", "server.hostname", "--remove", "server.port"])
        self.cc._validate_options()

    # unneuter these guys, since config doesn't required much mocking
    def test_config_list(self):
        self.cc._do_command = self._orig_do_command
        self.cc.main(["--list"])

    def test_config(self):
        self.cc._do_command = self._orig_do_command
        # if args is empty we default to sys.argv, so stub it
        sys.argv = ["subscription-manager", "config"]
        self.cc.main([])

    # testing this is a bit weird, since we are using a stub config
    # already, we kind of need to mock the stub config to validate
    def test_set_config(self):
        self.cc._do_command = self._orig_do_command

        baseurl = 'https://someserver.example.com/foo'
        self.cc.main(['--rhsm.baseurl', baseurl])
        self.assertEquals(managercli.cfg.store['rhsm.baseurl'], baseurl)

    def test_remove_config_default(self):
        with Capture() as cap:
            self.cc._do_command = self._orig_do_command
            self.cc.main(['--remove', 'rhsm.baseurl'])
        self.assertTrue('The default value for' in cap.out)

    def test_remove_config_section_does_not_exist(self):
        self.cc._do_command = self._orig_do_command
        self.assertRaises(SystemExit, self.cc.main, ['--remove', 'this.doesnotexist'])

    def test_remove_config_key_does_not_exist(self):
        self.cc._do_command = self._orig_do_command
        self.assertRaises(SystemExit, self.cc.main, ['--remove', 'rhsm.thisdoesnotexist'])

    def test_remove_config_key_not_dotted(self):
        self.cc._do_command = self._orig_do_command
        self.assertRaises(SystemExit, self.cc.main, ['--remove', 'notdotted'])


# Test Attach and Subscribe are the same
class TestAttachCommand(TestCliProxyCommand):
    command_class = managercli.AttachCommand

    def _test_quantity_exception(self, arg):
        try:
            self.cc.main(["--auto", "--quantity", arg])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, -1)
        else:
            self.fail("No Exception Raised")

    def test_zero_quantity(self):
        self._test_quantity_exception("0")

    def test_negative_quantity(self):
        self._test_quantity_exception("-1")

    def test_text_quantity(self):
        self._test_quantity_exception("JarJarBinks")

    def test_positive_quantity(self):
        self.cc.main(["--auto", "--quantity", "1"])
        self.cc._validate_options()

    def test_positive_quantity_with_plus(self):
        self.cc.main(["--auto", "--quantity", "+1"])
        self.cc._validate_options()

    def test_positive_quantity_as_float(self):
        self._test_quantity_exception("2.0")


# Test Attach and Subscribe are the same
class TestSubscribeCommand(TestAttachCommand):
    command_class = managercli.SubscribeCommand


class TestRemoveCommand(TestCliProxyCommand):
    command_class = managercli.RemoveCommand

    def test_validate_serial(self):
        self.cc.main(["--serial", "12345"])
        self.cc._validate_options()

    def test_validate_serial_not_numbers(self):
        self.cc.main(["--serial", "this is not a number"])
        try:
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_serial_no_value(self):
        try:
            self.cc.main(["--serial"])
        except SystemExit, e:
            self.assertEquals(e.code, 2)


class TestUnSubscribeCommand(TestRemoveCommand):
    command_class = managercli.UnSubscribeCommand


class TestFactsCommand(TestCliProxyCommand):
    command_class = managercli.FactsCommand


class TestImportCertCommand(TestCliCommand):
    command_class = managercli.ImportCertCommand

    def test_certificates(self):
        self.cc.main(["--certificate", "one", "--certificate", "two"])
        self.cc._validate_options()

    def test_no_certificates(self):
        try:
            self.cc.main([])
        except SystemExit, e:
            self.assertEquals(e.code, 2)

        try:
            self.cc._validate_options()
            self.fail("No exception raised")
        except Exception, e:
            pass
        except SystemExit, e:
            # there seems to be an optparse issue
            # here that depends on version, on f14
            # we get sysexit with return code 2  from main, on f15, we
            # get a -1 from validate_options
            # i18n_optparse returns 2 on no args
            self.assertEquals(e.code, -1)


class TestServiceLevelCommand(TestCliProxyCommand):
    command_class = managercli.ServiceLevelCommand

    def setUp(self):
        TestCliProxyCommand.setUp(self)
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()

    def test_main_server_url(self):
        server_url = "https://subscription.rhn.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])

    def test_org_requires_list_error(self):
        try:
            self.cc.main(["--org", "one"])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_org_requires_list_good(self):
        self.cc.main(["--org", "one", "--list"])

    def test_service_level_not_supported(self):
        self.cc.cp.setConsumer({})
        try:
            self.cc.set_service_level('JARJAR')
        except SystemExit, e:
            self.assertEquals(e.code, -1)
        else:
            self.fail("No Exception Raised")

    def test_service_level_supported(self):
        self.cc.cp.setConsumer({'serviceLevel': 'Jarjar'})
        try:
            self.cc.set_service_level('JRJAR')
        except SystemExit:
            self.fail("Exception Raised")


class TestReleaseCommand(TestCliProxyCommand):
    command_class = managercli.ReleaseCommand

    def _stub_connection(self):
        # er, first cc is command_class, second is ContentConnection
        def check_registration():
            consumer_info = {"consumer_name": "whatever",
                     "uuid": "doesnt really matter"}
            return consumer_info

        def _get_consumer_release():
            pass

        self.cc._get_consumer_release = _get_consumer_release
        managercli.check_registration = check_registration

    def test_main_proxy_url_release(self):
        proxy_host = "example.com"
        proxy_port = "3128"
        proxy_url = "%s:%s" % (proxy_host, proxy_port)
        self.cc.main(["--proxy", proxy_url])
        self._stub_connection()

        self._orig_do_command()
        self.assertEquals(proxy_host, self.cc.cc.proxy_hostname)

        self.assertEquals(proxy_url, self.cc.options.proxy_url)
        self.assertEquals(type(proxy_url), type(self.cc.options.proxy_url))
        self.assertEquals(proxy_host, self.cc.proxy_hostname)
        self.assertEquals(int(proxy_port), self.cc.proxy_port)


class TestVersionCommand(TestCliCommand):
    command_class = managercli.VersionCommand


class TestPluginsCommand(TestCliCommand):
    command_class = managercli.PluginsCommand


class TestOverrideCommand(TestCliProxyCommand):
    command_class = managercli.OverrideCommand

    def setUp(self):
        TestCliProxyCommand.setUp(self)

    def _test_exception(self, args):
        self.cc.main(args)
        self.assertRaises(SystemExit, self.cc._validate_options)

    def test_bad_add_format(self):
        self.assertRaises(SystemExit, self.cc.main, ["--add", "hello"])
        self.assertRaises(SystemExit, self.cc.main, ["--add", "hello:"])

    def test_add_and_remove_with_no_repo(self):
        self._test_exception(["--add", "hello:world"])
        self._test_exception(["--remove", "hello"])

    def test_add_and_remove_with_list(self):
        self._test_exception(["--add", "x:y", "--repo", "x", "--list"])
        self._test_exception(["--remove", "y", "--repo", "x", "--list"])

    def test_add_and_remove_with_remove_all(self):
        self._test_exception(["--add", "x:y", "--repo", "x", "--remove-all"])
        self._test_exception(["--remove", "y", "--repo", "x", "--remove-all"])

    def test_list_and_remove_all_mutuall_exclusive(self):
        self._test_exception(["--list", "--remove-all"])

    def test_no_bare_repo(self):
        self._test_exception(["--repo", "x"])

    def test_list_by_default(self):
        self.cc.main([])
        self.cc._validate_options()
        self.assertTrue(self.cc.options.list)

    def test_list_by_default_with_options_from_super_class(self):
        self.cc.main(["--proxy", "http://www.example.com", "--proxyuser", "foo", "--proxypassword", "bar"])
        self.cc._validate_options()
        self.assertTrue(self.cc.options.list)

    def test_add_with_multiple_colons(self):
        self.cc.main(["--repo", "x", "--add", "url:http://example.com"])
        self.cc._validate_options()
        self.assertEquals(self.cc.options.additions, {'url': 'http://example.com'})

    def test_add_and_remove_with_multi_repos(self):
        self.cc.main(["--repo", "x", "--repo", "y", "--add", "a:b", "--remove", "a"])
        self.cc._validate_options()
        self.assertEquals(self.cc.options.repos, ['x', 'y'])
        self.assertEquals(self.cc.options.additions, {'a': 'b'})
        self.assertEquals(self.cc.options.removals, ['a'])

    def test_list_and_remove_all_work_with_repos(self):
        self.cc.main(["--repo", "x", "--list"])
        self.cc._validate_options()
        self.cc.main(["--repo", "x", "--remove-all"])
        self.cc._validate_options()

    def _build_override(self, repo, name=None, value=None):
        data = {'contentLabel': repo}
        if name:
            data['name'] = name
        if value:
            data['value'] = value
        return data

    def test_list_function(self):
        data = [
            Override('x', 'hello', 'world'),
            Override('x', 'blast-off', 'space'),
            Override('y', 'goodbye', 'earth'),
            Override('z', 'greetings', 'mars')
        ]
        with Capture() as cap:
            self.cc._list(data, None)
            output = cap.out
            self.assertTrue(re.search('Repository: x', output))
            self.assertTrue(re.search('\s+hello:\s+world', output))
            self.assertTrue(re.search('\s+blast-off:\s+space', output))
            self.assertTrue(re.search('Repository: y', output))
            self.assertTrue(re.search('\s+goodbye:\s+earth', output))
            self.assertTrue(re.search('Repository: z', output))
            self.assertTrue(re.search('\s+greetings:\s+mars', output))

    def test_list_specific_repos(self):
        data = [
            Override('x', 'hello', 'world'),
            Override('z', 'greetings', 'mars')
        ]
        with Capture() as cap:
            self.cc._list(data, ['x'])
            output = cap.out
            self.assertTrue(re.search('Repository: x', output))
            self.assertTrue(re.search('\s+hello:\s+world', output))
            self.assertFalse(re.search('Repository: z', output))

    def test_list_nonexistant_repos(self):
        data = [
            Override('x', 'hello', 'world')
        ]
        with Capture() as cap:
            self.cc._list(data, ['x', 'z'])
            output = cap.out
            self.assertTrue(re.search("Nothing is known about 'z'", output))
            self.assertTrue(re.search('Repository: x', output))
            self.assertTrue(re.search('\s+hello:\s+world', output))


class TestSystemExit(unittest.TestCase):
    def setUp(self):
        sys.stderr = MockStderr()

    def test_a_msg(self):
        msg = "some message"
        with Capture() as cap:
            try:
                managercli.system_exit(1, msg)
            except SystemExit:
                pass
        self.assertEquals("%s\n" % msg, cap.err)

    def test_msgs(self):
        msgs = ["a", "b", "c"]
        with Capture() as cap:
            try:
                managercli.system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEquals("%s\n" % ("\n".join(msgs)), cap.err)

    def test_msg_and_exception(self):
        msgs = ["a", ValueError()]
        with Capture() as cap:
            try:
                managercli.system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEquals("%s\n\n" % msgs[0], cap.err)

    def test_msg_and_exception_no_str(self):
        class NoStrException(Exception):
            pass

        msgs = ["a", NoStrException()]
        with Capture() as cap:
            try:
                managercli.system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEquals("%s\n\n" % msgs[0], cap.err)

    def test_msg_unicode(self):
        msgs = [u"\u2620 \u2603 \u203D"]
        with Capture() as cap:
            try:
                managercli.system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEquals("%s\n" % msgs[0].encode("utf8"), cap.err)

    def test_msg_and_exception_str(self):
        class StrException(Exception):
            def __init__(self, msg):
                self.msg = msg

            def __str__(self):
                return self.msg

        msg = "bar"
        msgs = ["a", StrException(msg)]
        try:
            managercli.system_exit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n%s\n" % ("a", msg), sys.stderr.buffer)


class HandleExceptionTests(unittest.TestCase):
    def setUp(self):
        self.msg = "some thing to log home about"
        self.formatted_msg = "some thing else like: %s"
        sys.stderr = MockStderr()
        managercli.log = FakeLogger()

    def test_he(self):
        e = FakeException()
        try:
            managercli.handle_exception(self.msg, e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_unicode(self):
        e = Exception("Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
    #    e = FakeException(msg="Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        try:
            managercli.handle_exception("a: %s" % e, e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_socket_error(self):
        # these error messages are bare strings, so we need to update the tests
        # if those messages change
        expected_msg = 'Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.'
        managercli.log.set_expected_msg(expected_msg)
        try:
            managercli.handle_exception(self.msg, socket.error())
        except SystemExit, e:
            self.assertEquals(e.code, -1)
        self.assertEqual(managercli.log.expected_msg, expected_msg)

    def test_he_restlib_exception(self):
        e = connection.RestlibException(404, "this is a msg")
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_restlib_exception_unicode(self):
        e = connection.RestlibException(404,
            "Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        try:
            managercli.handle_exception("обновлении", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_bad_certificate(self):
        e = connection.BadCertificateException("/road/to/nowhwere")
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_remote_server_exception(self):
        e = connection.RemoteServerException(1984)
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_network_exception(self):
        e = connection.NetworkException(1337)
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_ssl_error(self):
        e = SSL.SSLError()
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)

    def test_he_ssl_wrong_host(self):
        e = SSL.Checker.WrongHost("expectedHost.example.com",
                                   "actualHost.example.com",
                                   "subjectAltName")
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, -1)


class TestFormatName(unittest.TestCase):
    def setUp(self):
        self.indent = 1
        self.max_length = 40

    def test_format_name_long(self):
        name = "This is a Really Long Name For A Product That We Do Not Want To See But Should Be Able To Deal With"
        format_name(name, self.indent, self.max_length)

    def test_format_name_short(self):
        name = "a"
        format_name(name, self.indent, self.max_length)

    def test_format_name_empty(self):
        name = ''
        new_name = format_name(name, self.indent, self.max_length)
        self.assertEquals(name, new_name)

    def test_format_name_null_width(self):
        name = "This is a Really Long Name For A Product That We Do Not Want To See But Should Be Able To Deal With"
        new_name = format_name(name, self.indent, None)
        self.assertEquals(name, new_name)

    def test_format_name_none(self):
        name = None
        new_name = format_name(name, self.indent, self.max_length)
        self.assertTrue(new_name is None)

    def test_leading_spaces(self):
        name = " " * 4 + "I have four leading spaces"
        new_name = format_name(name, 3, 10)
        self.assertEquals("    I have\n   four\n   leading\n   spaces", new_name)

    def test_leading_tabs(self):
        name = "\t" * 4 + "I have four leading tabs"
        new_name = format_name(name, self.indent, self.max_length)
        self.assertEquals("\t" * 4, new_name[0:4])


class TestNoneWrap(unittest.TestCase):
    def test_none_wrap(self):
        result = _none_wrap('foo %s %s', 'doberman pinscher', None)
        self.assertEquals(result, 'foo doberman pinscher None')


class TestColumnize(unittest.TestCase):
    def setUp(self):
        self.old_method = managercli.get_terminal_width
        managercli.get_terminal_width = Mock(return_value=500)

    def tearDown(self):
        managercli.get_terminal_width = self.old_method

    def test_columnize(self):
        result = columnize(["Hello:", "Foo:"], _echo, "world", "bar")
        self.assertEquals(result, "Hello: world\nFoo:   bar")

    def test_columnize_with_list(self):
        result = columnize(["Hello:", "Foo:"], _echo, ["world", "space"], "bar")
        self.assertEquals(result, "Hello: world\n       space\nFoo:   bar")

    def test_columnize_with_empty_list(self):
        result = columnize(["Hello:", "Foo:"], _echo, [], "bar")
        self.assertEquals(result, "Hello: \nFoo:   bar")

    @patch('subscription_manager.printing_utils.get_terminal_width')
    def test_columnize_with_small_term(self, term_width_mock):
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                _echo, "This is a testing string", "This_is_another_testing_string")
        expected = 'Hello\nHello\nHello\nHello\n:     This\n      is a\n      ' \
                'testin\n      g\n      string\nFoo\nFoo\nFoo\nFoo:  ' \
                'This_i\n      s_anot\n      her_te\n      sting_\n      string'
        self.assertNotEquals(result, expected)
        term_width_mock.return_value = 12
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                _echo, "This is a testing string", "This_is_another_testing_string")
        self.assertEquals(result, expected)

    def test_format_name_no_break_no_indent(self):
        result = format_name('testing string testing st', 0, 10)
        expected = 'testing\nstring\ntesting st'
        self.assertEquals(result, expected)

    def test_format_name_no_break(self):
        result = format_name('testing string testing st', 1, 11)
        expected = 'testing\n string\n testing st'
        self.assertEquals(result, expected)
        result = format_name('testing string testing st', 2, 12)
        expected = 'testing\n  string\n  testing st'
        self.assertEquals(result, expected)

    def test_format_name_break(self):
        result = format_name('a' * 10, 0, 10)
        expected = 'a' * 10
        self.assertEquals(result, expected)
        result = format_name('a' * 11, 0, 10)
        expected = 'a' * 10 + '\na'
        self.assertEquals(result, expected)
        result = format_name('a' * 11 + ' ' + 'a' * 9, 0, 10)
        expected = 'a' * 10 + '\na\n' + 'a' * 9
        self.assertEquals(result, expected)

    def test_format_name_break_indent(self):
        result = format_name('a' * 20, 1, 10)
        expected = 'a' * 9 + '\n ' + 'a' * 9 + '\n ' + 'aa'
        self.assertEquals(result, expected)

    @patch('subscription_manager.printing_utils.get_terminal_width')
    def test_columnize_multibyte(self, term_width_mock):
        multibyte_str = u"このシステム用に"
        term_width_mock.return_value = 40
        result = columnize([multibyte_str], _echo, multibyte_str)
        expected = u"このシステム用に このシステム用に"
        self.assertEquals(result, expected)
        term_width_mock.return_value = 14
        result = columnize([multibyte_str], _echo, multibyte_str)
        expected = u"このシ\nステム\n用に   このシ\n       ステム\n       用に"
        self.assertEquals(result, expected)
