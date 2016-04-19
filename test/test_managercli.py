# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import unittest
import re
import sys
import socket
import os
import tempfile
import contextlib


# for monkey patching config
import stubs

from subscription_manager import managercli, managerlib
from subscription_manager.injection import provide, \
        CERT_SORTER, PROD_DIR
from subscription_manager.managercli import get_installed_product_status, AVAILABLE_SUBS_MATCH_COLUMNS
from subscription_manager.printing_utils import format_name, columnize, \
        echo_columnize_callback, none_wrap_columnize_callback, highlight_by_filter_string_columnize_callback, FONT_BOLD, FONT_RED, FONT_NORMAL
from subscription_manager.repolib import Repo
from stubs import MockStderr, StubProductCertificate, StubEntitlementCertificate, \
        StubConsumerIdentity, StubProduct, StubUEP, StubProductDirectory, StubCertSorter, StubPool
from fixture import FakeException, FakeLogger, SubManFixture, \
        Capture, Matcher


import mock
from mock import patch
from mock import Mock
# for some exceptions
from rhsm import connection
from M2Crypto import SSL
from subscription_manager.overrides import Override


class InstalledProductStatusTests(SubManFixture):

    def test_entitlement_for_not_installed_product_shows_nothing(self):
        product_directory = StubProductDirectory([])
        provide(PROD_DIR, product_directory)

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())

        # no product certs installed...
        self.assertEquals(0, len(product_status))

    def test_entitlement_for_installed_product_shows_subscribed(self):
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        ent_cert = StubEntitlementCertificate('product1')

        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())

        self.assertEquals(1, len(product_status))
        self.assertEquals("subscribed", product_status[0][4])

    def test_expired_entitlement_for_installed_product_shows_expired(self):
        ent_cert = StubEntitlementCertificate('product1',
                end_date=(datetime.now() - timedelta(days=2)))

        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.expired_products['product1'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())

        self.assertEquals(1, len(product_status))
        self.assertEquals("expired", product_status[0][4])

    def test_no_entitlement_for_installed_product_shows_no_subscribed(self):
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.unentitled_products['product1'] = None  # prod cert unused here
        provide(CERT_SORTER, stub_sorter)

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())

        self.assertEquals(1, len(product_status))
        self.assertEquals("not_subscribed", product_status[0][4])

    def test_future_dated_entitlement_shows_future_subscribed(self):
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        ent_cert = StubEntitlementCertificate('product1',
                    start_date=(datetime.now() + timedelta(days=1365)))
        stub_sorter = StubCertSorter()
        stub_sorter.future_products['product1'] = [ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())
        self.assertEquals(1, len(product_status))
        self.assertEquals("future_subscribed", product_status[0][4])

    def test_one_product_with_two_entitlements_lists_product_twice(self):
        ent_cert = StubEntitlementCertificate('product1',
            ['product2', 'product3'], sockets=10)
        product_directory = StubProductDirectory(pids=['product1'])
        provide(PROD_DIR, product_directory)
        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert, ent_cert]
        provide(CERT_SORTER, stub_sorter)

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())

        # only "product" is installed
        self.assertEquals(1, len(product_status))

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

        product_status = get_installed_product_status(product_directory,
                None, StubUEP())

        # neither product3 or product 2 are installed
        self.assertEquals(1, len(product_status))
        self.assertEquals("product1", product_status[0][0])
        self.assertEquals("subscribed", product_status[0][4])

    def test_one_subscription_with_bundled_products_lists_once_part_two(self):
        ent_cert = StubEntitlementCertificate('product1',
            ['product2', 'product3'], sockets=10)

        prod_dir = StubProductDirectory(pids=['product1', 'product2'])
        provide(PROD_DIR, prod_dir)
        stub_sorter = StubCertSorter()
        stub_sorter.valid_products['product1'] = [ent_cert]
        stub_sorter.valid_products['product2'] = [ent_cert]

        provide(CERT_SORTER, stub_sorter)

        product_status = get_installed_product_status(prod_dir,
                None, StubUEP())

        # product3 isn't installed
        self.assertEquals(2, len(product_status))
        self.assertEquals("product2", product_status[0][0])
        self.assertEquals("subscribed", product_status[0][4])
        self.assertEquals("product1", product_status[1][0])
        self.assertEquals("subscribed", product_status[1][4])


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

    def setUp(self, hide_do=True):
        super(TestCliCommand, self).setUp()
        self.cc = self.command_class()
        # neuter the _do_command, since this is mostly
        # for testing arg parsing
        if hide_do:
            self._orig_do_command = self.cc._do_command
            self.cc._do_command = self._do_command

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

    # docker error message should output to stderr
    @patch('subscription_manager.managercli.rhsm.config.in_container')
    def test_cli_in_container_error_message(self, mock_in_container):
        sys.argv = ["subscription-manager", "version"]
        mock_in_container.return_value = True
        err_msg = 'subscription-manager is disabled when running inside a container.'\
                  ' Please refer to your host system for subscription management.\n\n'
        try:
            self.cc.main()
        except SystemExit, e:
            self.assertEquals(os.EX_CONFIG, e.code)
        self.assertEquals(err_msg, sys.stderr.buffer)


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
        server_url = "https://subscription.rhsm.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])


class TestEnvironmentsCommand(TestCliProxyCommand):
    command_class = managercli.EnvironmentsCommand

    def test_main_server_url(self):
        server_url = "https://subscription.rhsm.redhat.com/subscription"
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
            self.assertEquals(e.code, os.EX_USAGE)
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

    def test_force_and_consumerid(self):
        self._test_exception(["--consumerid", "22", "--force"])

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
        server_url = "https://subscription.rhsm.redhat.com/subscription"
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
                     'management_enabled': True,
                     'attributes': [{'name': 'is_virt_only',
                                     'value': 'false'}],
                     'pool_type': 'Some Type',
                     'quantity': '4',
                     'service_level': '',
                     'service_type': '',
                     'contractNumber': '5',
                     'subscriptionNumber': '6',
                     'multi-entitlement': 'false',
                     'endDate': '',
                     'suggested': '2'}]
        mget_ents.return_value = create_pool_list()

        with Capture() as cap:
            list_command.main(['list', '--available'])
        self.assertTrue('888888888888' in cap.out)

    def test_print_consumed_no_ents(self):
        with Capture() as captured:
            self.cc.print_consumed()

        lines = captured.out.split("\n")
        self.assertEquals(len(lines) - 1, 1, "Error output consists of more than one line.")

    def test_list_installed_with_ctfilter(self):
        installed_product_certs = [
            StubProductCertificate(product=StubProduct(name="test product*", product_id="8675309")),
            StubProductCertificate(product=StubProduct(name="another(?) test\\product", product_id="123456"))
        ]

        test_data = [
            ("", (False, False)),
            ("input string", (False, False)),
            ("*product", (False, True)),
            ("*product*", (True, True)),
            ("*test pro*uct*", (True, False)),
            ("*test pro?uct*", (True, False)),
            ("*test pr*ct*", (True, False)),
            ("*test pr?ct*", (False, False)),
            ("*another*", (False, True)),
            ("*product\\*", (True, False)),
            ("*product?", (True, False)),
            ("*product?*", (True, False)),
            ("*(\\?)*", (False, True)),
            ("*test\\\\product", (False, True)),
        ]

        stub_sorter = StubCertSorter()

        for product_cert in installed_product_certs:
            product = product_cert.products[0]
            stub_sorter.installed_products[product.id] = product_cert

        provide(CERT_SORTER, stub_sorter)

        for (test_num, data) in enumerate(test_data):
            with Capture() as captured:
                list_command = managercli.ListCommand()
                list_command.main(["list", "--installed", "--matches", data[0]])

            for (index, expected) in enumerate(data[1]):
                if expected:
                    self.assertTrue(installed_product_certs[index].name in captured.out, "Expected product was not found in output for test data %i" % test_num)
                else:
                    self.assertFalse(installed_product_certs[index].name in captured.out, "Unexpected product was found in output for test data %i" % test_num)

    def test_list_consumed_with_ctfilter(self):
        consumed = [
            StubEntitlementCertificate(product=StubProduct(name="Test Entitlement 1", product_id="123"), provided_products=[
                "test product a",
                "beta product 1",
                "shared product",
                "troll* product?"
            ]),

            StubEntitlementCertificate(product=StubProduct(name="Test Entitlement 2", product_id="456"), provided_products=[
                "test product b",
                "beta product 1",
                "shared product",
                "back\\slash"
            ])
        ]

        test_data = [
            ("", (False, False)),
            ("test entitlement ?", (True, True)),
            ("*entitlement 1", (True, False)),
            ("*entitlement 2", (False, True)),
            ("input string", (False, False)),
            ("*product", (True, True)),
            ("*product*", (True, True)),
            ("shared pro*nopenopenope", (False, False)),
            ("*another*", (False, False)),
            ("*product\\?", (True, False)),
            ("*product ?", (True, True)),
            ("*product?*", (True, True)),
            ("*\\?*", (True, False)),
            ("*\\\\*", (False, True)),
            ("*k\\s*", (False, True)),
            ("*23", (True, False)),
            ("45?", (False, True)),
        ]

        for stubby in consumed:
            self.ent_dir.certs.append(stubby)

        for (test_num, data) in enumerate(test_data):
            with Capture() as captured:
                list_command = managercli.ListCommand()
                list_command.main(["list", "--consumed", "--matches", data[0]])

            for (index, expected) in enumerate(data[1]):
                if expected:
                    self.assertTrue(consumed[index].order.name in captured.out, "Expected product was not found in output for test data %i" % test_num)
                else:
                    self.assertFalse(consumed[index].order.name in captured.out, "Unexpected product was found in output for test data %i" % test_num)

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

        with Capture() as captured:
            self.cc.print_consumed(service_level="NotFound")

        lines = captured.out.split("\n")
        self.assertEquals(len(lines) - 1, 1, "Error output consists of more than one line.")

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

    def test_list_installed_with_pidonly(self):
        installed_product_certs = [
            StubProductCertificate(product=StubProduct(name="test product*", product_id="8675309")),
            StubProductCertificate(product=StubProduct(name="another(?) test\\product", product_id="123456"))
        ]

        stub_sorter = StubCertSorter()

        for product_cert in installed_product_certs:
            product = product_cert.products[0]
            stub_sorter.installed_products[product.id] = product_cert

        provide(CERT_SORTER, stub_sorter)

        try:
            with Capture() as captured:
                list_command = managercli.ListCommand()
                list_command.main(["list", "--installed", "--pool-only"])

            self.fail("Expected error did not occur")
        except SystemExit:
            for cert in installed_product_certs:
                self.assertFalse(cert.products[0].id in captured.out)

    def test_list_consumed_with_pidonly(self):
        consumed = [
            StubEntitlementCertificate(product=StubProduct(name="Test Entitlement 1", product_id="123"), pool=StubPool("abc"), provided_products=[
                "test product a",
                "beta product 1",
                "shared product",
                "troll* product?"
            ]),

            StubEntitlementCertificate(product=StubProduct(name="Test Entitlement 2", product_id="456"), pool=StubPool("def"), provided_products=[
                "test product b",
                "beta product 1",
                "shared product",
                "back\\slash"
            ])
        ]

        for stubby in consumed:
            self.ent_dir.certs.append(stubby)

        with Capture() as captured:
            list_command = managercli.ListCommand()
            list_command.main(["list", "--consumed", "--pool-only"])

        for cert in consumed:
            self.assertFalse(cert.order.name in captured.out)
            self.assertTrue(cert.pool.id in captured.out)


class TestUnRegisterCommand(TestCliProxyCommand):
    command_class = managercli.UnRegisterCommand


class TestRedeemCommand(TestCliProxyCommand):
    command_class = managercli.RedeemCommand


class TestReposCommand(TestCliCommand):
    command_class = managercli.ReposCommand

    def setUp(self):
        super(TestReposCommand, self).setUp(False)
        self.cc.cp = Mock()

    def check_output_for_repos(self, output, repos):
        """
        Checks the given output string for the specified repos' ids.

        Returns a tuple of booleans specifying whether or not the repo in the corresponding position
        was found in the output.
        """
        searches = []
        for repo in repos:
            # Impl note: This may break if a repo's ID contains special regex characters.
            searches.append(re.search("^Repo ID:\\s+%s$" % repo.id, output, re.MULTILINE) is not None)

        return tuple(searches)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_default(self, mock_invoker):
        self.cc.main()
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, True, True), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list(self, mock_invoker):
        self.cc.main(["--list"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, True, True), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list_with_enabled(self, mock_invoker):
        self.cc.main(["--list", "--list-enabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, True, True), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list_with_disabled(self, mock_invoker):
        self.cc.main(["--list", "--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, True, True), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list_with_enabled_and_disabled(self, mock_invoker):
        self.cc.main(["--list", "--list-disabled", "--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, True, True), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list_enabled(self, mock_invoker):
        self.cc.main(["--list-enabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, False, False), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list_disabled(self, mock_invoker):
        self.cc.main(["--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((False, True, True), result)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_list_enabled_and_disabled(self, mock_invoker):
        self.cc.main(["--list-enabled", "--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        # Execute command with our mock stdout capturing the output
        sys.stdout = self.mock_stdout
        self.cc._do_command()
        sys.stdout = sys.__stdout__

        result = self.check_output_for_repos(self.mock_stdout.buffer, repos)
        self.assertEquals((True, True, True), result)

    def test_enable(self):
        self.cc.main(["--enable", "one", "--enable", "two"])
        self.cc._validate_options()

    def test_disable(self):
        self.cc.main(["--disable", "one", "--disable", "two"])
        self.cc._validate_options()

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_set_repo_status(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('x'), Repo('y'), Repo('z')]
        items = [('0', 'x'), ('0', 'y')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [{'contentLabel': i, 'name': 'enabled', 'value':
            '0'} for (action, i) in items]

        # The list of overrides sent to setContentOverrides is really a set of
        # dictionaries (since we don't know the order of the overrides).
        # However, since the dict class is not hashable, we can't actually use
        # a set.  So we need a custom matcher to make sure that the
        # JSON passed in to setContentOverrides is what we expect.
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_set_repo_status_with_wildcards(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('0', 'z*')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [{'contentLabel': i.id, 'name': 'enabled', 'value':
            '0'} for i in repos]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_set_repo_status_disable_all_enable_some(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('0', '*'), ('1', 'zoo'),
            ('1', 'zip')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [
            {'contentLabel': 'zebra', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zoo', 'name': 'enabled', 'value': '1'},
            {'contentLabel': 'zip', 'name': 'enabled', 'value': '1'}
        ]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_set_repo_status_enable_all_disable_some(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('1', '*'), ('0', 'zoo'),
            ('0', 'zip')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [
            {'contentLabel': 'zebra', 'name': 'enabled', 'value': '1'},
            {'contentLabel': 'zoo', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zip', 'name': 'enabled', 'value': '0'}
        ]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @mock.patch("subscription_manager.managercli.RepoActionInvoker")
    def test_set_repo_status_enable_all_disable_all(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('1', '*'), ('0', '*')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [
            {'contentLabel': 'zebra', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zoo', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zip', 'name': 'enabled', 'value': '0'}
        ]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

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
        items = [('0', 'z*')]

        self.cc._set_repo_status(repos, None, items)
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

    @classmethod
    def setUpClass(cls):
        # Create temp file(s) for processing pool IDs
        cls.tempfiles = [
            tempfile.mkstemp(),
            tempfile.mkstemp(),
            tempfile.mkstemp()
        ]

        os.write(cls.tempfiles[0][0], "pool1 pool2   pool3 \npool4\npool5\r\npool6\t\tpool7\n  pool8\n\n\n")
        os.close(cls.tempfiles[0][0])

        os.write(cls.tempfiles[1][0], "pool1 pool2   pool3 \npool4\npool5\r\npool6\t\tpool7\n  pool8\n\n\n")
        os.close(cls.tempfiles[1][0])

        # The third temp file intentionally left empty for testing empty sets of data.
        os.close(cls.tempfiles[2][0])

    @classmethod
    def tearDownClass(cls):
        # Unlink temp files
        for file in cls.tempfiles:
            os.unlink(file[1])

    def _test_quantity_exception(self, arg):
        try:
            self.cc.main(["--pool", "test-pool-id", "--quantity", arg])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_USAGE)
        else:
            self.fail("No Exception Raised")

    def _test_auto_and_quantity_exception(self):
        try:
            self.cc.main(["--auto", "--quantity", "6"])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_USAGE)
        else:
            self.fail("No Exception Raised")

    def _test_auto_default_and_quantity_exception(self):
        try:
            self.cc.main(["--quantity", "3"])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_USAGE)
        else:
            self.fail("No Exception Raised")

    def test_zero_quantity(self):
        self._test_quantity_exception("0")

    def test_negative_quantity(self):
        self._test_quantity_exception("-1")

    def test_text_quantity(self):
        self._test_quantity_exception("JarJarBinks")

    def test_positive_quantity(self):
        self.cc.main(["--pool", "test-pool-id", "--quantity", "1"])
        self.cc._validate_options()

    def test_positive_quantity_with_plus(self):
        self.cc.main(["--pool", "test-pool-id", "--quantity", "+1"])
        self.cc._validate_options()

    def test_positive_quantity_as_float(self):
        self._test_quantity_exception("2.0")

    def _test_pool_file_processing(self, file, expected):
        self.cc.main(["--file", file])
        self.cc._validate_options()

        self.assertEquals(expected, self.cc.options.pool)

    def test_pool_option_or_auto_option(self):
        self.cc.main(["--auto", "--pool", "1234"])
        self.assertRaises(SystemExit, self.cc._validate_options)

    def test_servicelevel_option_but_no_auto_option(self):
        with self.mock_stdin(open(self.tempfiles[1][1])):
            self.cc.main(["--servicelevel", "Super", "--file", "-"])
            self.assertRaises(SystemExit, self.cc._validate_options)

    def test_servicelevel_option_with_pool_option(self):
        self.cc.main(["--servicelevel", "Super", "--pool", "1232342342313"])
        # need a assertRaises that checks a SystemsExit code and message
        self.assertRaises(SystemExit, self.cc._validate_options)

    def test_just_pools_option(self):
        self.cc.main(["--pool", "1234"])
        self.cc._validate_options()

    def test_just_auto_option(self):
        self.cc.main(["--auto"])
        self.cc._validate_options()

    def test_no_options_defaults_to_auto(self):
        self.cc.main([])
        self.cc._validate_options()

    @contextlib.contextmanager
    def mock_stdin(self, fileobj):
        org_stdin = sys.stdin
        sys.stdin = fileobj

        try:
            yield
        finally:
            sys.stdin = org_stdin

    def test_pool_stdin_processing(self):
        with self.mock_stdin(open(self.tempfiles[1][1])):
            self._test_pool_file_processing('-', ["pool1", "pool2", "pool3", "pool4", "pool5", "pool6", "pool7", "pool8"])

    def test_pool_stdin_empty(self):
        try:
            with self.mock_stdin(open(self.tempfiles[2][1])):
                self.cc.main(["--file", "-"])
                self.cc._validate_options()

        except SystemExit, e:
            self.assertEquals(e.code, os.EX_DATAERR)
        else:
            self.fail("No Exception Raised")

    def test_pool_file_processing(self):
        self._test_pool_file_processing(self.tempfiles[0][1], ["pool1", "pool2", "pool3", "pool4", "pool5", "pool6", "pool7", "pool8"])

    def test_pool_file_empty(self):
        try:
            self.cc.main(["--file", self.tempfiles[2][1]])
            self.cc._validate_options()

        except SystemExit, e:
            self.assertEquals(e.code, os.EX_DATAERR)
        else:
            self.fail("No Exception Raised")

    def test_pool_file_invalid(self):
        try:
            self.cc.main(["--file", "nonexistant_file.nope"])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_DATAERR)
        else:
            self.fail("No Exception Raised")


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
            self.assertEquals(e.code, os.EX_USAGE)

    def test_serial_no_value(self):
        try:
            self.cc.main(["--serial"])
        except SystemExit, e:
            self.assertEquals(e.code, 2)

    def test_validate_access_to_remove_by_pool(self):
        self.cc.main(["--pool", "a2ee88488bbd32ed8edfa2"])
        self.cc.cp._capabilities = ["remove_by_pool_id"]
        self.cc._validate_options()

    def test_validate_no_access_to_remove_by_pool(self):
        self.cc.main(["--pool", "a2ee88488bbd32ed8edfa2"])
        try:
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, 69)


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
            # get os.EX_USAGE from validate_options
            # i18n_optparse returns 2 on no args
            self.assertEquals(e.code, os.EX_USAGE)


class TestServiceLevelCommand(TestCliProxyCommand):
    command_class = managercli.ServiceLevelCommand

    def setUp(self):
        TestCliProxyCommand.setUp(self)
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()

    def test_main_server_url(self):
        server_url = "https://subscription.rhsm.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])

    def test_org_requires_list_error(self):
        try:
            self.cc.main(["--org", "one"])
            self.cc._validate_options()
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_USAGE)

    def test_org_requires_list_good(self):
        self.cc.main(["--org", "one", "--list"])

    def test_service_level_not_supported(self):
        self.cc.cp.setConsumer({})
        try:
            self.cc.set_service_level('JARJAR')
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_UNAVAILABLE)
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

        def _get_consumer_release():
            pass

        self.cc._get_consumer_release = _get_consumer_release

    def test_main_proxy_url_release(self):
        proxy_host = "example.com"
        proxy_port = "3128"
        proxy_url = "%s:%s" % (proxy_host, proxy_port)
        self.cc.main(["--proxy", proxy_url])
        self._stub_connection()

        self._orig_do_command()

        # FIXME: too many stubs atm to make this meaningful
        #self.assertEquals(proxy_host, self.cc.cp_provider.content_connection.proxy_hostname)

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
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_unicode(self):
        e = Exception("Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
    #    e = FakeException(msg="Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        try:
            managercli.handle_exception("a: %s" % e, e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_socket_error(self):
        # these error messages are bare strings, so we need to update the tests
        # if those messages change
        expected_msg = 'Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.'
        managercli.log.set_expected_msg(expected_msg)
        try:
            managercli.handle_exception(self.msg, socket.error())
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)
        self.assertEqual(managercli.log.expected_msg, expected_msg)

    def test_he_restlib_exception(self):
        e = connection.RestlibException(404, "this is a msg")
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_restlib_exception_unicode(self):
        e = connection.RestlibException(404,
            "Ошибка при обновлении системных данных (см. /var/log/rhsm/rhsm.log")
        try:
            managercli.handle_exception("обновлении", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_bad_certificate(self):
        e = connection.BadCertificateException("/road/to/nowhwere")
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_remote_server_exception(self):
        e = connection.RemoteServerException(1984)
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_network_exception(self):
        e = connection.NetworkException(1337)
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_ssl_error(self):
        e = SSL.SSLError()
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)

    def test_he_ssl_wrong_host(self):
        e = SSL.Checker.WrongHost("expectedHost.example.com",
                                   "actualHost.example.com",
                                   "subjectAltName")
        try:
            managercli.handle_exception("huh", e)
        except SystemExit, e:
            self.assertEquals(e.code, os.EX_SOFTWARE)


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


class TestHighlightByFilter(unittest.TestCase):
    def test_highlight_by_filter_string(self):
        args = ['Super Test Subscription']
        kwargs = {"filter_string": "Super*",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_callback("Subscription Name:    %s", *args, **kwargs)
        self.assertEquals(result, 'Subscription Name:    ' + FONT_BOLD + FONT_RED + 'Super Test Subscription' + FONT_NORMAL)

    def test_highlight_by_filter_string_single(self):
        args = ['Super Test Subscription']
        kwargs = {"filter_string": "*Subscriptio?",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_callback("Subscription Name:    %s", *args, **kwargs)
        self.assertEquals(result, 'Subscription Name:    ' + FONT_BOLD + FONT_RED + 'Super Test Subscription' + FONT_NORMAL)

    def test_highlight_by_filter_string_all(self):
        args = ['Super Test Subscription']
        kwargs = {"filter_string": "*",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_callback("Subscription Name:    %s", *args, **kwargs)
        self.assertEquals(result, 'Subscription Name:    Super Test Subscription')

    def test_highlight_by_filter_string_exact(self):
        args = ['Premium']
        kwargs = {"filter_string": "Premium",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Service Level:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_callback("Service Level:    %s", *args, **kwargs)
        self.assertEquals(result, 'Service Level:    ' + FONT_BOLD + FONT_RED + 'Premium' + FONT_NORMAL)

    def test_highlight_by_filter_string_list_row(self):
        args = ['Awesome-os-stacked']
        kwargs = {"filter_string": "Awesome*",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_callback("    %s", *args, **kwargs)
        self.assertEquals(result, '    ' + FONT_BOLD + FONT_RED + 'Awesome-os-stacked' + FONT_NORMAL)


class TestNoneWrap(unittest.TestCase):
    def test_none_wrap(self):
        result = none_wrap_columnize_callback('foo %s %s', 'doberman pinscher', None)
        self.assertEquals(result, 'foo doberman pinscher None')


class TestColumnize(unittest.TestCase):
    def setUp(self):
        self.old_method = managercli.get_terminal_width
        managercli.get_terminal_width = Mock(return_value=500)

    def tearDown(self):
        managercli.get_terminal_width = self.old_method

    def test_columnize(self):
        result = columnize(["Hello:", "Foo:"], echo_columnize_callback, "world", "bar")
        self.assertEquals(result, "Hello: world\nFoo:   bar")

    def test_columnize_with_list(self):
        result = columnize(["Hello:", "Foo:"], echo_columnize_callback, ["world", "space"], "bar")
        self.assertEquals(result, "Hello: world\n       space\nFoo:   bar")

    def test_columnize_with_empty_list(self):
        result = columnize(["Hello:", "Foo:"], echo_columnize_callback, [], "bar")
        self.assertEquals(result, "Hello: \nFoo:   bar")

    @patch('subscription_manager.printing_utils.get_terminal_width')
    def test_columnize_with_small_term(self, term_width_mock):
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                echo_columnize_callback, "This is a testing string", "This_is_another_testing_string")
        expected = 'Hello\nHello\nHello\nHello\n:     This\n      is a\n      ' \
                'testin\n      g\n      string\nFoo\nFoo\nFoo\nFoo:  ' \
                'This_i\n      s_anot\n      her_te\n      sting_\n      string'
        self.assertNotEquals(result, expected)
        term_width_mock.return_value = 12
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                echo_columnize_callback, "This is a testing string", "This_is_another_testing_string")
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
        result = columnize([multibyte_str], echo_columnize_callback, multibyte_str)
        expected = u"このシステム用に このシステム用に"
        self.assertEquals(result, expected)
        term_width_mock.return_value = 14
        result = columnize([multibyte_str], echo_columnize_callback, multibyte_str)
        expected = u"このシ\nステム\n用に   このシ\n       ステム\n       用に"
        self.assertEquals(result, expected)
