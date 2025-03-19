import sys

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli
from subscription_manager.entcertlib import CONTENT_ACCESS_CERT_TYPE

from ..stubs import StubEntitlementCertificate, StubProduct

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
