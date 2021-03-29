# -*- coding: utf-8 -*-

import os
import sys

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli
from subscription_manager.entcertlib import CONTENT_ACCESS_CERT_TYPE
from subscription_manager.injection import provide, CERT_SORTER

from ..stubs import StubProductCertificate, StubEntitlementCertificate, \
        StubProduct, StubCertSorter, StubPool
from ..fixture import Capture

from mock import patch, Mock, MagicMock


class TestListCommand(TestCliProxyCommand):
    command_class = managercli.ListCommand
    valid_date = '2018-05-01'

    def setUp(self):
        super(TestListCommand, self).setUp(False)
        self.indent = 1
        self.max_length = 40
        self.cert_with_service_level = StubEntitlementCertificate(
            StubProduct("test-product"), service_level="Premium")
        self.cert_with_content_access = StubEntitlementCertificate(
            StubProduct("test-product"), entitlement_type=CONTENT_ACCESS_CERT_TYPE)
        argv_patcher = patch.object(sys, 'argv', ['subscription-manager', 'list'])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)

    def _test_afterdate_option(self, argv, method, should_exit=True, expected_exit_code=0):
        msg = ""
        with patch.object(sys, 'argv', argv):
            try:
                method()
            except SystemExit as e:
                self.assertEqual(e.code, expected_exit_code,
                    """Cli should have exited with code '{}', got '{}'""".format(expected_exit_code,
                        e.code))
                fail = False
            except Exception as e:
                fail = True
                msg = "Expected SystemExit, got \'\'\'{}\'\'\'".format(e)
            else:
                fail = should_exit
                if fail:
                    msg = "Expected SystemExit, No Exception was raised"

            if fail:
                self.fail(msg)

    def test_afterdate_option_bad_date(self):
        argv = ['subscription-manager', 'list', '--all', '--available', '--afterdate',
                'not_a_real_date']
        self._test_afterdate_option(argv, self.cc.main, expected_exit_code=os.EX_DATAERR)

    def test_afterdate_option_no_date(self):
        argv = ['subscription-manager', 'list', '--all', '--available', '--afterdate']
        # Error code of 2 is expected from optparse in this case.
        self._test_afterdate_option(argv, self.cc.main, expected_exit_code=2)

    def test_afterdate_option_missing_options(self):
        # Just missing "available"
        argv = ['subscription-manager', 'list', '--afterdate', self.valid_date, '--all']
        self._test_afterdate_option(argv, self.cc.main, expected_exit_code=os.EX_USAGE)

        # Missing both
        argv = ['subscription-manager', 'list', '--afterdate', self.valid_date]
        self._test_afterdate_option(argv, self.cc.main, expected_exit_code=os.EX_USAGE)

    def test_afterdate_option_with_ondate(self):
        argv = ['subscription-manager', 'list', '--afterdate', self.valid_date, '--ondate',
            self.valid_date]
        self._test_afterdate_option(argv, self.cc.main, expected_exit_code=os.EX_USAGE)

    @patch('subscription_manager.managerlib.get_available_entitlements')
    def test_afterdate_option_valid(self, es):
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
                     'service_type': '',
                     'roles': 'awsome server',
                     'service_level': '',
                     'usage': 'Testing',
                     'addons': 'ADDON1',
                     'contractNumber': '5',
                     'multi-entitlement': 'false',
                     'startDate': '',
                     'endDate': '',
                     'suggested': '2'}]
        es.return_value = create_pool_list()

        argv = ['subscription-manager', 'list', '--all', '--available', '--afterdate', self.valid_date]
        self._test_afterdate_option(argv, self.cc.main, should_exit=False)

    @patch('subscription_manager.managerlib.get_available_entitlements')
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
                     'service_type': '',
                     'roles': 'awesome server',
                     'service_level': '',
                     'usage': 'Production',
                     'addons': '',
                     'contractNumber': '5',
                     'multi-entitlement': 'false',
                     'startDate': '',
                     'endDate': '',
                     'suggested': '2'}]
        mget_ents.return_value = create_pool_list()

        with Capture() as cap:
            list_command.main(['--available'])
        self.assertTrue('888888888888' in cap.out)

    @patch('subscription_manager.managerlib.get_available_entitlements')
    def test_available_syspurpose_attr(self, mget_ents):
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
                     'service_type': '',
                     'roles': 'Awesome Server, Cool Server',
                     'service_level': 'Premium',
                     'usage': 'Production',
                     'addons': 'ADDON1,ADDON2',
                     'contractNumber': '5',
                     'multi-entitlement': 'false',
                     'startDate': '',
                     'endDate': '',
                     'suggested': '2'}]
        mget_ents.return_value = create_pool_list()

        with Capture() as cap:
            list_command.main(['--available'])
        self.assertTrue('ADDON1\n' in cap.out)
        self.assertTrue('Awesome Server\n' in cap.out)
        self.assertTrue('Production' in cap.out)
        self.assertTrue('Premium' in cap.out)

    def test_print_consumed_no_ents(self):
        with Capture() as captured:
            self.cc.print_consumed()

        lines = captured.out.split("\n")
        self.assertEqual(len(lines) - 1, 1, "Error output consists of more than one line.")

    def test_list_installed_with_ctfilter(self):
        installed_product_certs = [
            StubProductCertificate(product=StubProduct(name="test product*", product_id="8675309")),
            StubProductCertificate(product=StubProduct(name="another(?) test\\product", product_id="123456"))
        ]

        test_data = [
            ("", (True, True)),
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
                list_command.main(["--installed", "--matches", data[0]])

            for (index, expected) in enumerate(data[1]):
                if expected:
                    self.assertTrue(installed_product_certs[index].name in captured.out,
                                    "Expected product was not found in output for test data %i" % test_num)
                else:
                    self.assertFalse(installed_product_certs[index].name in captured.out,
                                     "Unexpected product was found in output for test data %i" % test_num)

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
                list_command.main(["--consumed", "--matches", data[0]])

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
        self.assertEqual(len(lines) - 1, 1, "Error output consists of more than one line.")

    def test_print_consumed_prints_enitlement_with_service_level_match(self):
        self.ent_dir.certs.append(self.cert_with_service_level)
        self.cc.sorter = Mock()
        self.cc.sorter.get_subscription_reasons_map = Mock()
        self.cc.sorter.get_subscription_reasons_map.return_value = {}
        self.cc.print_consumed(service_level="Premium")

    def test_print_consumed_ignores_content_access_cert(self):
        self.ent_dir.certs.append(self.cert_with_content_access)
        with Capture() as captured:
            self.cc.print_consumed(service_level="NotFound")

        lines = captured.out.split("\n")
        self.assertEqual(len(lines) - 1, 1, "Error output consists of more than one line.")

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
                list_command.main(["--installed", "--pool-only"])

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
            list_command.main(["--consumed", "--pool-only"])

        for cert in consumed:
            self.assertFalse(cert.order.name in captured.out)
            self.assertTrue(cert.pool.id in captured.out)

    def test_list_consumed_syspurpose_attr_version34(self):
        """
        When version of entitlement certificate is 3.4, then subscription-manager should print syspurpose
        attributes from the certificate.
        """
        product = StubProduct("product1")
        ent_cert = StubEntitlementCertificate(product)
        ent_cert.order.usage = "Development"
        ent_cert.order.roles = [u"SP Server", u"SP Starter"]
        ent_cert.order.addons = [u"ADDON1", u"ADDON2"]
        ent_cert.version = MagicMock()
        ent_cert.version.major = 3
        ent_cert.version.minor = 4
        self.ent_dir.certs.append(ent_cert)
        self.cc.sorter = Mock()
        self.cc.sorter.get_subscription_reasons_map = Mock()
        self.cc.sorter.get_subscription_reasons_map.return_value = {}
        with Capture() as captured:
            self.cc.print_consumed()
            self.assertTrue("Add-ons:" in captured.out)
            self.assertTrue("ADDON1" in captured.out)
            self.assertTrue("ADDON2" in captured.out)
            self.assertTrue("Usage:" in captured.out)
            self.assertTrue("Development" in captured.out)
            self.assertTrue("Roles:" in captured.out)
            self.assertTrue("SP Server" in captured.out)
            self.assertTrue("SP Starter" in captured.out)

    def test_list_consumed_no_syspurpose_attr_version33(self):
        """
        When the version of certificate is older then 3.4, then do not print syspurpose attributes, because
        there cannot be any.
        """
        product = StubProduct("product1")
        ent_cert = StubEntitlementCertificate(product)
        ent_cert.version = MagicMock()
        ent_cert.version.major = 3
        ent_cert.version.minor = 3
        self.ent_dir.certs.append(ent_cert)
        self.cc.sorter = Mock()
        self.cc.sorter.get_subscription_reasons_map = Mock()
        self.cc.sorter.get_subscription_reasons_map.return_value = {}
        with Capture() as captured:
            self.cc.print_consumed()
            self.assertFalse("Add-ons:" in captured.out)
            self.assertFalse("Usage:" in captured.out)
            self.assertFalse("Roles:" in captured.out)
