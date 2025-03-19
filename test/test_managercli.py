import unittest

import sys
import socket
import os

from subscription_manager import syspurposelib
from subscription_manager import managercli, managerlib
from subscription_manager.injection import provide, PROD_DIR
from rhsmlib.services.products import InstalledProducts
from subscription_manager.cli_command.cli import handle_exception, system_exit
from subscription_manager.cli_command import cli

from .stubs import StubUEP, StubProductDirectory
from .fixture import FakeException, FakeLogger, SubManFixture, Capture

from unittest.mock import patch

# for some exceptions
from rhsm import connection
from rhsm.https import ssl


class InstalledProductStatusTests(SubManFixture):
    def test_entitlement_for_not_installed_product_shows_nothing(self):
        product_directory = StubProductDirectory([])
        provide(PROD_DIR, product_directory)

        product_status = InstalledProducts(StubUEP()).list()

        # no product certs installed...
        self.assertEqual(0, len(product_status))


class TestCli(SubManFixture):
    def setUp(self):
        syspurpose_patch = patch("syspurpose.files.SyncedStore")
        sp_patch = syspurpose_patch.start()
        self.addCleanup(sp_patch.stop)
        super(TestCli, self).setUp()
        syspurposelib.USER_SYSPURPOSE = self.write_tempfile("{}").name

    def tearDown(self):
        super(TestCli, self).tearDown()
        syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

    def test_cli(self):
        cli = managercli.ManagerCLI()
        self.assertTrue("register" in cli.cli_commands)

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
        best_match = cli._find_best_match(["subscription-manager", "version"])
        self.assertEqual(best_match.name, "version")

    # shouldn't match on -sdf names
    def test_cli_find_best_match_no_dash(self):
        cli = managercli.ManagerCLI()
        best_match = cli._find_best_match(["subscription-manager", "--version"])
        self.assertEqual(best_match, None)


class TestCliCommand(SubManFixture):
    command_class = cli.CliCommand

    def setUp(self, hide_do=True):
        super(TestCliCommand, self).setUp()
        self.cc = self.command_class()

        if hide_do:
            # patch the _do_command with a mock
            self._orig_do_command = self.cc._do_command
            do_command_patcher = patch.object(self.command_class, "_do_command")
            self.mock_do_command = do_command_patcher.start()
            self.addCleanup(do_command_patcher.stop)

    def test_main_no_args(self):
        try:
            # we fall back to sys.argv if there
            # is no args passed in, so stub out
            # sys.argv for test
            with patch.object(sys, "argv", ["subscription-manager"]):
                self.cc.main()
        except SystemExit as e:
            # 2 == no args given
            self.assertEqual(e.code, 2)

    def test_main_empty_args(self):
        try:
            with patch.object(sys, "argv", ["subscription-manager"]):
                self.cc.main([])
        except SystemExit as e:
            # 2 == no args given
            self.assertEqual(e.code, 2)

    def test_unknown_args_cause_exit(self):
        with Capture() as cap, patch.object(
            sys,
            "argv",
            # test with some subcommand; sub-man prints help without it
            ["subscription-manager", "register", "--foo", "bar", "baz"],
        ):
            try:
                self.cc.main()
            except SystemExit as e:
                self.assertEqual(e.code, os.EX_USAGE)
            self.assertEqual("subscription-manager: error: no such option: --foo bar baz\n", cap.err)

    def test_command_has_correlation_id(self):
        self.assertIsNotNone(self.cc.correlation_id)

    def _main_help(self, args):
        with Capture() as cap:
            try:
                self.cc.main(args)
            except SystemExit as e:
                # --help/-h returns 0
                self.assertEqual(e.code, 0)
        output = cap.out.strip()
        # I could test for strings here, but that
        # would break if we run tests in a locale/lang
        self.assertTrue(len(output) > 0)

    def test_main_short_help(self):
        self._main_help(["-h"])

    def test_main_long_help(self):
        self._main_help(["--help"])

    # docker error message should output to stderr
    @patch("subscription_manager.cli_command.cli.rhsm.config.in_container")
    def test_cli_in_container_error_message(self, mock_in_container):
        with patch.object(sys, "argv", ["subscription-manager", "version"]):
            mock_in_container.return_value = True
            err_msg = (
                "subscription-manager is operating in container mode. "
                "Use your host system to manage subscriptions.\n\n"
            )
            with Capture() as cap:
                try:
                    self.cc.main()
                except SystemExit as e:
                    self.assertEqual(os.EX_CONFIG, e.code)
            self.assertEqual(err_msg, cap.err)

    def _test_exception(self, args):
        try:
            self.cc.main(args)
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)
        else:
            self.fail("No Exception Raised")

    def _test_no_exception(self, args):
        try:
            self.cc.main(args)
            self.cc._validate_options()
        except SystemExit:
            self.fail("Exception Raised")


# for command classes that expect proxy related cli args
class TestCliProxyCommand(TestCliCommand):
    def test_main_proxy_url(self):
        proxy_host = "example.com"
        proxy_port = "3128"
        proxy_url = "%s:%s" % (proxy_host, proxy_port)
        self.cc.main(["--proxy", proxy_url])
        self.assertEqual(proxy_url, self.cc.options.proxy_url)
        self.assertEqual(type(proxy_url), type(self.cc.options.proxy_url))
        self.assertEqual(proxy_host, self.cc.proxy_hostname)
        self.assertEqual(int(proxy_port), self.cc.proxy_port)

    def test_main_proxy_user(self):
        proxy_user = "buster"
        self.cc.main(["--proxyuser", proxy_user])
        self.assertEqual(proxy_user, self.cc.proxy_user)

    def test_main_proxy_password(self):
        proxy_password = "nomoresecrets"
        self.cc.main(["--proxypassword", proxy_password])
        self.assertEqual(proxy_password, self.cc.proxy_password)


class TestSystemExit(unittest.TestCase):
    def test_a_msg(self):
        msg: str = "some message"
        with Capture() as cap:
            try:
                system_exit(1, msg)
            except SystemExit:
                pass
        self.assertEqual("%s\n" % msg, cap.err)

    def test_msg_unicode(self):
        msg: str = "\u2620 \u2603 \u203d"
        with Capture() as cap:
            try:
                system_exit(1, msg)
            except SystemExit:
                pass
        captured: str = cap.err
        self.assertEqual("%s\n" % msg, captured)

    def test_only_exception(self):
        ex: ValueError = ValueError("test message")
        with Capture() as cap:
            try:
                system_exit(1, ex)
            except SystemExit:
                pass
        self.assertEqual("%s\n" % str(ex), cap.err)

    def test_only_exception_unicode(self):
        ex: ValueError = ValueError("\u2620 \u2603 \u203d")
        with Capture() as cap:
            try:
                system_exit(1, ex)
            except SystemExit:
                pass
        self.assertEqual("%s\n" % str(ex), cap.err)


class HandleExceptionTests(unittest.TestCase):
    def setUp(self):
        self.msg = "some thing to log home about"
        self.formatted_msg = "some thing else like: %s"

    def test_he(self):
        e = FakeException()
        try:
            handle_exception(self.msg, e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_unicode(self):
        e = Exception("Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        #    e = FakeException(msg="Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        try:
            handle_exception("a: %s" % e, e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    @patch("subscription_manager.managercli.log", FakeLogger())
    def test_he_socket_error(self):
        # these error messages are bare strings, so we need to update the tests
        # if those messages change
        expected_msg = (
            "Network error, unable to connect to server. "
            "Please see /var/log/rhsm/rhsm.log for more information."
        )
        managercli.log.set_expected_msg(expected_msg)
        try:
            handle_exception(self.msg, socket.error())
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)
        self.assertEqual(managercli.log.expected_msg, expected_msg)

    def test_he_restlib_exception(self):
        e = connection.RestlibException(404, "this is a msg")
        try:
            handle_exception("huh", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_restlib_exception_unicode(self):
        e = connection.RestlibException(
            404, "Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log"
        )
        try:
            handle_exception("обновлении", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_bad_certificate(self):
        sslerr = ssl.SSLError(5, "some ssl error")
        e = connection.BadCertificateException("/road/to/nowhwere", sslerr)
        try:
            handle_exception("huh", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_remote_server_exception(self):
        e = connection.RemoteServerException(1984)
        try:
            handle_exception("huh", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_unknowncontent_exception(self):
        e = connection.UnknownContentException(1337)
        try:
            handle_exception("huh", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_ssl_error(self):
        e = ssl.SSLError()
        try:
            handle_exception("huh", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)
