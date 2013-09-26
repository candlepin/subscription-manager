# -*- coding: utf-8 -*-
import unittest
import sys
import socket

# for monkey patching config
import stubs

from subscription_manager import managercli, managerlib
from subscription_manager.managercli import format_name, columnize, \
        _echo, _none_wrap
from stubs import MockStderr, MockStdout, \
        StubEntitlementCertificate, \
        StubConsumerIdentity, StubProduct, StubUEP
from test_handle_gui_exception import FakeException, FakeLogger
from fixture import SubManFixture

import mock
from mock import patch
from mock import Mock
# for some exceptions
from rhsm import connection
from M2Crypto import SSL

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
        sys.stdout = stubs.MockStdout()
        sys.stderr = stubs.MockStderr()

    def _restore_stdout(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def tearDown(self):
        self._restore_stdout()

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
        SubManFixture.setUp(self)
        self.cc = self.command_class()
        # neuter the _do_command, since this is mostly
        # for testing arg parsing
        self._orig_do_command = self.cc._do_command
        self.cc._do_command = self._do_command
        self.cc.assert_should_be_registered = self._asert_should_be_registered

        # stub out uep
        managercli.connection.UEPConnection = self._uep_connection
        self.mock_stdout = MockStdout()
        self.mock_stderr = MockStderr()
        sys.stdout = self.mock_stdout
        sys.stderr = self.mock_stderr

    def _restore_stdout(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def tearDown(self):
        self._restore_stdout()

    def _uep_connection(self, *args, **kwargs):
        pass

    def _do_command(self):
        pass

    def _asert_should_be_registered(self):
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
        mstdout = MockStdout()
        sys.stdout = mstdout
        try:
            self.cc.main(args)
        except SystemExit, e:
            # --help/-h returns 0
            self.assertEquals(e.code, 0)
        sys.stdout = sys.__stdout__
        # I could test for strings here, but that
        # would break if we run tests in a locale/lang
        assert len(mstdout.buffer) > 0

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

    def test_no_library(self):
        self.cc.cp = StubUEP()
        environments = []
        environments.append({'name': 'JarJar'})
        environments.append({'name': 'Library'})
        environments.append({'name': 'library'})
        environments.append({'name': 'Binks'})
        self.cc.cp.setEnvironmentList(environments)
        results = self.cc._get_enviornments("Anikan")
        self.assertTrue(len(results) == 2)
        self.assertTrue(results[0]['name'] == 'JarJar')
        self.assertTrue(results[1]['name'] == 'Binks')


class TestRegisterCommand(TestCliProxyCommand):
    command_class = managercli.RegisterCommand

    def setUp(self):
        TestCliProxyCommand.setUp(self)
        self.cc.consumerIdentity = StubConsumerIdentity

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

    @mock.patch.object(managercli.ConsumerIdentity, 'existsAndValid')
    @mock.patch.object(managercli.ConsumerIdentity, 'exists')
    @mock.patch('subscription_manager.managercli.check_registration')
    def test_none_wrap_available_pool_id(self, mcli, mc_exists, mc_exists_and_valid):
        listCommand = managercli.ListCommand()

        def create_pool_list(self, one, two, three, four):
            return [{'productName': 'dummy-name', 'productId': 'dummy-id',
                     'id': '888888888888', 'attributes': [{'name': 'is_virt_only', 'value': 'false'}],
                     'quantity': '4', 'service_level': '', 'service_type': '',
                     'multi-entitlement': 'false', 'endDate': '', 'suggested': '2',
                     'providedProducts': []}]
        managerlib.get_available_entitlements = create_pool_list

        mc_exists_and_valid.return_value = True
        mc_exists.return_value = True

        mcli.return_value = {'consumer_name': 'stub_name', 'uuid': 'stub_uuid'}
        listCommand.main(['list', '--available'])
        self.assertTrue('888888888888' in sys.stdout.buffer)

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

    def test_list(self):
        self.cc.main(["--list"])
        self.cc._validate_options()

    def test_enable(self):
        self.cc.main(["--enable", "one", "--enable", "two"])
        self.cc._validate_options()

    def test_disable(self):
        self.cc.main(["--disable", "one", "--disable", "two"])
        self.cc._validate_options()

    @mock.patch("subscription_manager.managercli.RepoFile")
    def test_set_repo_status(self, mock_repofile):
        repos = mock.MagicMock()
        repo = mock.MagicMock()
        mock_repofile_inst = mock_repofile.return_value

        repos.__iter__.return_value = iter([repo])

        repo_dict = {'enabled': '1'}

        def getitem(name):
            return repo_dict[name]

        def setitem(name, val):
            repo_dict[name] = val

        repo.__getitem__.side_effect = getitem
        repo.__setitem__.side_effect = setitem
        repo.id = "foo"

        items = ["foo"]
        self.cc._set_repo_status(repos, items, False)
        mock_repofile_inst.read.assert_called()
        mock_repofile_inst.update.assert_called_with(repo)
        mock_repofile_inst.write.assert_called()


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
        self.cc._do_command = self._orig_do_command
        self.cc.main(['--remove', 'rhsm.baseurl'])
        self.assertTrue('The default value for' in self.mock_stdout.buffer)

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


class TestSystemExit(unittest.TestCase):
    def setUp(self):
        sys.stderr = MockStderr()

    def test_a_msg(self):
        msg = "some message"
        try:
            managercli.system_exit(1, msg)
        except SystemExit:
            pass
        self.assertEquals("%s\n" % msg, sys.stderr.buffer)

    def test_msgs(self):
        msgs = ["a", "b", "c"]
        try:
            managercli.system_exit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n" % ("\n".join(msgs)), sys.stderr.buffer)

    def test_msg_and_exception(self):
        msgs = ["a", ValueError()]
        try:
            managercli.system_exit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n\n" % msgs[0], sys.stderr.buffer)

    def test_msg_and_exception_no_str(self):
        class NoStrException(Exception):
            pass

        msgs = ["a", NoStrException()]
        try:
            managercli.system_exit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n\n" % msgs[0], sys.stderr.buffer)

    def test_msg_unicode(self):
        msgs = [u"\u2620 \u2603 \u203D"]
        try:
            managercli.system_exit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n" % msgs[0].encode("utf8"), sys.stderr.buffer)

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
        sys.stdout = MockStdout()
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

    def test_columnize_with_small_term(self):
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                _echo, "This is a testing string", "This_is_another_testing_string")
        expected = 'Hello\nHello\nHello\nHello\n:     This\n      is a\n      ' \
                'testin\n      g\n      string\nFoo\nFoo\nFoo\nFoo:  ' \
                'This_i\n      s_anot\n      her_te\n      sting_\n      string'
        self.assertNotEquals(result, expected)
        managercli.get_terminal_width = Mock(return_value=12)
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

    def test_columnize_multibyte(self):
        multibyte_str = u"このシステム用に"
        managercli.get_terminal_width = Mock(return_value=40)
        result = columnize([multibyte_str], _echo, multibyte_str)
        expected = u"このシステム用に このシステム用に"
        self.assertEquals(result, expected)
        managercli.get_terminal_width = Mock(return_value=14)
        result = columnize([multibyte_str], _echo, multibyte_str)
        expected = u"このシ\nステム\n用に   このシ\n       ステム\n       用に"
        self.assertEquals(result, expected)
