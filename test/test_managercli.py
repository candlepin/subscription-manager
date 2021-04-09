# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datetime import datetime, timedelta
import sys
import socket
import os

import six

from subscription_manager import syspurposelib
from subscription_manager import managercli, managerlib
from subscription_manager.injection import provide, CERT_SORTER, PROD_DIR
from rhsmlib.services.products import InstalledProducts
from subscription_manager.cli_command.cli import handle_exception, system_exit
from subscription_manager.cli_command import cli

from .stubs import StubEntitlementCertificate, StubUEP, StubProductDirectory, \
        StubCertSorter
from .fixture import FakeException, FakeLogger, SubManFixture, \
        Capture

from mock import patch, MagicMock
from nose import SkipTest

# for some exceptions
from rhsm import connection
from rhsm.https import ssl
if six.PY2:
    from M2Crypto import SSL


class InstalledProductStatusTests(SubManFixture):

    def test_entitlement_for_not_installed_product_shows_nothing(self):
        product_directory = StubProductDirectory([])
        provide(PROD_DIR, product_directory)

        product_status = InstalledProducts(StubUEP()).list()

        # no product certs installed...
        self.assertEqual(0, len(product_status))

    def test_entitlement_for_installed_product_shows_subscribed(self):
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        ent_cert = StubEntitlementCertificate('product1')

        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()

        self.assertEqual(1, len(product_status))
        self.assertEqual("subscribed", product_status[0][4])

    def test_expired_entitlement_for_installed_product_shows_expired(self):
        ent_cert = StubEntitlementCertificate('product1',
                end_date=(datetime.now() - timedelta(days=2)))

        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.expired_products['product1'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()

        self.assertEqual(1, len(product_status))
        self.assertEqual("expired", product_status[0][4])

    def test_no_entitlement_for_installed_product_shows_no_subscribed(self):
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.unentitled_products['product1'] = None  # prod cert unused here
        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()

        self.assertEqual(1, len(product_status))
        self.assertEqual("not_subscribed", product_status[0][4])

    def test_future_dated_entitlement_shows_future_subscribed(self):
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        ent_cert = StubEntitlementCertificate('product1',
                    start_date=(datetime.now() + timedelta(days=1365)))
        stub_sorter = StubCertSorter()
        stub_sorter.future_products['product1'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()
        self.assertEqual(1, len(product_status))
        self.assertEqual("future_subscribed", product_status[0][4])

    def test_one_product_with_two_entitlements_lists_product_twice(self):
        ent_cert = StubEntitlementCertificate('product1',
            ['product2', 'product3'], sockets=10)
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert, ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()

        # only "product" is installed
        self.assertEqual(1, len(product_status))

    def test_one_subscription_with_bundled_products_lists_once(self):
        ent_cert = StubEntitlementCertificate('product1',
            ['product2', 'product3'], sockets=10)
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert]
        stub_sorter.valid_products['product2'] = [ent_cert]
        stub_sorter.valid_products['product3'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()

        # neither product3 or product 2 are installed
        self.assertEqual(1, len(product_status))
        self.assertEqual("product1", product_status[0][0])
        self.assertEqual("subscribed", product_status[0][4])

    def test_one_subscription_with_bundled_products_lists_once_part_two(self):
        ent_cert = StubEntitlementCertificate('product1',
            ['product2', 'product3'], sockets=10)

        prod_dir = StubProductDirectory(pids=['product1', 'product2'])
        provide(PROD_DIR, prod_dir)
        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert]
        stub_sorter.valid_products['product2'] = [ent_cert]

        provide(CERT_SORTER, stub_sorter)

        product_status = InstalledProducts(StubUEP()).list()

        # product3 isn't installed
        self.assertEqual(2, len(product_status))
        self.assertEqual("product1", product_status[0][0])
        self.assertEqual("subscribed", product_status[0][4])
        self.assertEqual("product2", product_status[1][0])
        self.assertEqual("subscribed", product_status[1][4])


class TestCli(SubManFixture):
    def setUp(self):
        syspurpose_patch = patch('syspurpose.files.SyncedStore')
        sp_patch = syspurpose_patch.start()
        self.addCleanup(sp_patch.stop)
        super(TestCli, self).setUp()
        syspurposelib.USER_SYSPURPOSE = self.write_tempfile("{}").name

    def tearDown(self):
        super(TestCli, self).tearDown()
        syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

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
        self.assertEqual(best_match.name, 'version')

    # shouldn't match on -sdf names
    def test_cli_find_best_match_no_dash(self):
        cli = managercli.ManagerCLI()
        best_match = cli._find_best_match(['subscription-manager', '--version'])
        self.assertEqual(best_match, None)


class TestCliCommand(SubManFixture):
    command_class = cli.CliCommand

    def setUp(self, hide_do=True):
        super(TestCliCommand, self).setUp()
        self.cc = self.command_class()

        if hide_do:
            # patch the _do_command with a mock
            self._orig_do_command = self.cc._do_command
            do_command_patcher = patch.object(self.command_class, '_do_command')
            self.mock_do_command = do_command_patcher.start()
            self.addCleanup(do_command_patcher.stop)

    def test_main_no_args(self):
        try:
            # we fall back to sys.argv if there
            # is no args passed in, so stub out
            # sys.argv for test
            with patch.object(sys, 'argv', ['subscription-manager']):
                self.cc.main()
        except SystemExit as e:
            # 2 == no args given
            self.assertEqual(e.code, 2)

    def test_main_empty_args(self):
        try:
            with patch.object(sys, 'argv', ['subscription-manager']):
                self.cc.main([])
        except SystemExit as e:
            # 2 == no args given
            self.assertEqual(e.code, 2)

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
    @patch('subscription_manager.cli_command.cli.rhsm.config.in_container')
    def test_cli_in_container_error_message(self, mock_in_container):
        with patch.object(sys, 'argv', ['subscription-manager', 'version']):
            mock_in_container.return_value = True
            err_msg = 'subscription-manager is disabled when running inside a container.'\
                      ' Please refer to your host system for subscription management.\n\n'
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


class TestProxyConnection(SubManFixture):
    """
    This class is used for testing test_proxy_connection from class CliCommand
    """

    def setUp(self):
        super(TestProxyConnection, self).setUp()
        # Temporary stop patcher of test_proxy_connection, because we need to test behavior of
        # original function
        self.test_proxy_connection_patcher.stop()

    def tearDown(self):
        # Start patcher again
        self.test_proxy_connection_patcher.start()
        super(TestProxyConnection, self).tearDown()

    @patch('socket.socket')
    def test_proxy_connection_hostname_and_port(self, sock):
        """
        Test functionality of test_proxy_connection()
        """
        sock_instance = sock.return_value
        sock_instance.settimeout = MagicMock()
        sock_instance.connect_ex = MagicMock(return_value=0)
        sock_instance.close = MagicMock()

        the_cli = cli.CliCommand()
        the_cli.test_proxy_connection()

        # Expected values are from fake configuration file (see stub.py)
        sock_instance.connect_ex.assert_called_once_with(('notaproxy.grimlock.usersys.redhat.com', 4567))


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
        msg = "some message"
        with Capture() as cap:
            try:
                system_exit(1, msg)
            except SystemExit:
                pass
        self.assertEqual("%s\n" % msg, cap.err)

    def test_msgs(self):
        msgs = ["a", "b", "c"]
        with Capture() as cap:
            try:
                system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEqual("%s\n" % ("\n".join(msgs)), cap.err)

    def test_msg_and_exception(self):
        msgs = ["a", ValueError()]
        with Capture() as cap:
            try:
                system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEqual("%s\n\n" % msgs[0], cap.err)

    def test_msg_and_exception_no_str(self):
        class NoStrException(Exception):
            pass

        msgs = ["a", NoStrException()]
        with Capture() as cap:
            try:
                system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEqual("%s\n\n" % msgs[0], cap.err)

    def test_msg_unicode(self):
        msgs = [u"\u2620 \u2603 \u203D"]
        with Capture() as cap:
            try:
                system_exit(1, msgs)
            except SystemExit:
                pass
        if six.PY2:
            captured = cap.err.decode('utf-8')
        else:
            captured = cap.err
        self.assertEqual(u"%s\n" % msgs[0], captured)

    def test_msg_and_exception_str(self):
        class StrException(Exception):
            def __init__(self, msg):
                self.msg = msg

            def __str__(self):
                return self.msg

        msg = "bar"
        msgs = ["a", StrException(msg)]
        with Capture() as cap:
            try:
                system_exit(1, msgs)
            except SystemExit:
                pass
        self.assertEqual("%s\n%s\n" % ("a", msg), cap.err)


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

    @patch('subscription_manager.managercli.log', FakeLogger())
    def test_he_socket_error(self):
        # these error messages are bare strings, so we need to update the tests
        # if those messages change
        expected_msg = 'Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.'
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
        e = connection.RestlibException(404,
            "Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        try:
            handle_exception("обновлении", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)

    def test_he_bad_certificate(self):
        e = connection.BadCertificateException("/road/to/nowhwere")
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

    def test_he_network_exception(self):
        e = connection.NetworkException(1337)
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

    def test_he_ssl_wrong_host(self):
        if not six.PY2:
            raise SkipTest("M2Crypto-specific interface. Not used with Python 3.")
        e = SSL.Checker.WrongHost("expectedHost.example.com",
                                   "actualHost.example.com",
                                   "subjectAltName")
        try:
            handle_exception("huh", e)
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_SOFTWARE)
