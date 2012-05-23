# -*- coding: utf-8 -*-
import unittest
import sys
import socket

from subscription_manager import managercli
from stubs import MockStdout, MockStderr, StubProductDirectory, \
        StubEntitlementDirectory, StubEntitlementCertificate, \
        StubConsumerIdentity, StubProduct, StubUEP
from test_handle_gui_exception import FakeException, FakeLogger


class TestCliCommand(unittest.TestCase):
    command_class = managercli.CliCommand

    def setUp(self):
        self.cc = self.command_class(ent_dir=StubEntitlementDirectory([]),
                                     prod_dir=StubProductDirectory([]))
        # neuter the _do_command, since this is mostly
        # for testing arg parsing
        self.cc._do_command = self._do_command
        self.cc.assert_should_be_registered = self._asert_should_be_registered

        # stub out uep
        managercli.connection.UEPConnection = self._uep_connection
        sys.stdout = MockStdout()
        sys.stderr = MockStderr()

    def tearDown(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

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
        self.assertEquals(proxy_port, self.cc.proxy_port)

    def test_main_proxy_user(self):
        proxy_user = "buster"
        self.cc.main(["--proxyuser", proxy_user])
        self.assertEquals(proxy_user, self.cc.proxy_user)

    def test_main_proxy_password(self):
        proxy_password = "nomoresecrets"
        self.cc.main(["--proxypassword", proxy_password])
        self.assertEquals(proxy_password, self.cc.proxy_password)

class TestCliCommandServerurl(TestCliCommand):
    def test_main_server_url(self):
        server_url = "https://subscription.rhn.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

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


class TestEnvironmentsCommand(TestCliProxyCommand):
    command_class = managercli.EnvironmentsCommand

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

    def test_key_and_no_org(self):
        self._test_exception(["--activationkey", "key"])

    def test_key_and_org(self):
        self._test_no_exception(["--activationkey", "key", "--org", "org"])

    def test_empty_string_key_and_org(self):
        self._test_exception(["--activationkey=", "--org", "org"])

    def test_keys_and_username(self):
        self._test_exception(["--username", "bob", "--activationkey", "key"])

    def test_env_and_no_org(self):
        self._test_exception(["--env", "env"])

    def test_env_and_org(self):
        self._test_no_exception(["--env", "env", "--org", "org"])

    def test_no_commands(self):
        self._test_no_exception([])


class TestListCommand(TestCliProxyCommand):
    command_class = managercli.ListCommand

    def setUp(self):
        self.indent = 1
        self.max_length = 40
        self.cert_with_service_level = StubEntitlementCertificate(
            StubProduct("test-product"), service_level="Premium")
        TestCliProxyCommand.setUp(self)

    def test_none_wrap(self):
        listCommand = managercli.ListCommand()
        result = listCommand._none_wrap('foo %s %s', 'doberman pinscher', None)
        self.assertEquals(result, 'foo doberman pinscher None')

    def test_format_name_long(self):
        name = "This is a Really Long Name For A Product That We Do Not Want To See But Should Be Able To Deal With"
        self.cc._format_name(name, self.indent, self.max_length)

    def test_format_name_short(self):
        name = "a"
        self.cc._format_name(name, self.indent, self.max_length)

    def test_format_name_empty(self):
        name = 'e'
        self.cc._format_name(name, self.indent, self.max_length)

    def test_print_consumed_no_ents(self):
        ent_dir = StubEntitlementDirectory([])
        try:
            self.cc.print_consumed(ent_dir)
            self.fail("Should have exited.")
        except SystemExit:
            pass

    def test_print_consumed_one_ent_one_product(self):
        product = StubProduct("product1")
        ent_dir = StubEntitlementDirectory([
            StubEntitlementCertificate(product)])
        self.cc.print_consumed(ent_dir)

    def test_print_consumed_one_ent_no_product(self):
        ent_dir = StubEntitlementDirectory([
            StubEntitlementCertificate(product=None)])
        self.cc.print_consumed(ent_dir)

    def test_print_consumed_prints_nothing_with_no_service_level_match(self):
        ent_dir = StubEntitlementDirectory([self.cert_with_service_level])
        try:
            self.cc.print_consumed(ent_dir, service_level="NotFound")
            self.fail("Should have exited since an entitlement with the " + \
                      "specified service level does not exist.")
        except SystemExit:
            pass

    def test_print_consumed_prints_enitlement_with_service_level_match(self):
        ent_dir = StubEntitlementDirectory([self.cert_with_service_level])
        self.cc.print_consumed(ent_dir, service_level="Premium")

    def test_filter_only_specified_service_level(self):
        pools = [{'service_level':'Level1'},
                 {'service_level':'Level2'},
                 {'service_level':'Level3'}]
        filtered = self.cc._filter_pool_json_by_service_level(pools, "Level2")
        self.assertEqual(1, len(filtered))
        self.assertEqual("Level2", filtered[0]['service_level'])

    def test_no_pool_with_specified_filter(self):
        pools = [{'service_level':'Level1'}]
        filtered = self.cc._filter_pool_json_by_service_level(pools, "NotFound")
        self.assertEqual(0, len(filtered))


class TestUnRegisterCommand(TestCliProxyCommand):
    command_class = managercli.UnRegisterCommand


class TestRedeemCommand(TestCliProxyCommand):
    command_class = managercli.RedeemCommand


class TestReposCommand(TestCliCommand):
    command_class = managercli.ReposCommand


class TestConfigCommand(TestCliCommand):
    command_class = managercli.ConfigCommand

    def test_list(self):
        self.cc.main(["--list"])
        self.cc._validate_options()

    def test_remove(self):
        self.cc.main(["--remove", "server.hostname", "--remove", "server.port"])
        self.cc._validate_options()


class TestSubscribeCommand(TestCliProxyCommand):
    command_class = managercli.SubscribeCommand

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


class TestUnSubscribeCommand(TestCliProxyCommand):
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


class TestReleaseCommand(TestCliProxyCommand):
    command_class = managercli.ReleaseCommand

    # def test_no_product_certs
    # def test_no_rhel_product

    # def test_invalid_content_url


class TestVersionCommand(TestCliCommand):
    command_class = managercli.VersionCommand


class TestSystemExit(unittest.TestCase):
    def setUp(self):
        sys.stderr = MockStderr()

    def test_a_msg(self):
        msg = "some message"
        try:
            managercli.systemExit(1, msg)
        except SystemExit:
            pass
        self.assertEquals("%s\n" % msg, sys.stderr.buffer)

    def test_msgs(self):
        msgs = ["a", "b", "c"]
        try:
            managercli.systemExit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n" % ("\n".join(msgs)), sys.stderr.buffer)

    def test_msg_and_exception(self):
        msgs = ["a", ValueError()]
        try:
            managercli.systemExit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n\n" % msgs[0], sys.stderr.buffer)

    def test_msg_and_exception_no_str(self):
        class NoStrException(Exception):
            pass

        msgs = ["a", NoStrException()]
        try:
            managercli.systemExit(1, msgs)
        except SystemExit:
            pass
        self.assertEquals("%s\n\n" % msgs[0], sys.stderr.buffer)

    def test_msg_unicode(self):
        msgs = [u"\u2620 \u2603 \u203D"]
        try:
            managercli.systemExit(1, msgs)
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
            managercli.systemExit(1, msgs)
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
