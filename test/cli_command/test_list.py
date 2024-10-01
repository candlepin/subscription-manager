import sys

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli
from subscription_manager.entcertlib import CONTENT_ACCESS_CERT_TYPE
from subscription_manager.injection import provide, CERT_SORTER

from ..stubs import StubProductCertificate, StubEntitlementCertificate, StubProduct, StubCertSorter
from ..fixture import Capture

from unittest.mock import patch


class TestListCommand(TestCliProxyCommand):
    command_class = managercli.ListCommand
    valid_date = "2018-05-01"

    def setUp(self):
        super(TestListCommand, self).setUp(False)
        self.indent = 1
        self.max_length = 40
        self.cert_with_service_level = StubEntitlementCertificate(
            StubProduct("test-product"), service_level="Premium"
        )
        self.cert_with_content_access = StubEntitlementCertificate(
            StubProduct("test-product"), entitlement_type=CONTENT_ACCESS_CERT_TYPE
        )
        argv_patcher = patch.object(sys, "argv", ["subscription-manager", "list"])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)

    def test_list_installed(self):
        """
        Test output of 'subscription-manager list --installed'
        """
        installed_product_certs = [
            StubProductCertificate(product=StubProduct(name="test product", product_id="8675309")),
            StubProductCertificate(product=StubProduct(name="another test product", product_id="123456")),
        ]

        stub_sorter = StubCertSorter()

        for product_cert in installed_product_certs:
            product = product_cert.products[0]
            stub_sorter.installed_products[product.id] = product_cert

        provide(CERT_SORTER, stub_sorter)

        with Capture() as captured:
            list_command = managercli.ListCommand()
            list_command.main(["--installed"])
            assert "Product Name:" in captured.out
            assert "Product ID:" in captured.out
            assert "Version:" in captured.out
            assert "Arch:" in captured.out

    def test_list_installed_with_ctfilter(self):
        installed_product_certs = [
            StubProductCertificate(product=StubProduct(name="test product*", product_id="8675309")),
            StubProductCertificate(product=StubProduct(name="another(?) test\\product", product_id="123456")),
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

        for test_num, data in enumerate(test_data):
            with Capture() as captured:
                list_command = managercli.ListCommand()
                list_command.main(["--installed", "--matches", data[0]])

            for index, expected in enumerate(data[1]):
                if expected:
                    self.assertTrue(
                        installed_product_certs[index].name in captured.out,
                        "Expected product was not found in output for test data %i" % test_num,
                    )
                else:
                    self.assertFalse(
                        installed_product_certs[index].name in captured.out,
                        "Unexpected product was found in output for test data %i" % test_num,
                    )
