from subscription_manager import managercli
from rhsm.certificate2 import CONTENT_ACCESS_CERT_TYPE

from ..stubs import StubUEP
from ..fixture import SubManFixture, Capture

from unittest.mock import Mock, patch


MOCK_SERVICE_STATUS_SCA = {
    "status": "Disabled",
    "status_id": "disabled",
    "reasons": {},
    "reason_ids": {},
    "valid": True,
}

MOCK_SERVICE_STATUS_ENTITLEMENT = {
    "status": "Current",
    "status_id": "valid",
    "reasons": {},
    "reason_ids": {},
    "valid": True,
}


class TestStatusCommand(SubManFixture):
    command_class = managercli.StatusCommand

    def setUp(self):
        super(TestStatusCommand, self).setUp()
        self.cc = self.command_class()
        patcher = patch("subscription_manager.cli_command.status.entitlement")
        self.entitlement_mock = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_entitlement_instance = Mock()
        self.mock_entitlement_instance.get_status = Mock(return_value=MOCK_SERVICE_STATUS_SCA)
        self.entitlement_mock.EntitlementService = Mock(return_value=self.mock_entitlement_instance)

    def test_disabled_status_sca_mode(self):
        """
        Test status, when SCA mode is used
        """
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({"status": "disabled"})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        mock_cert = Mock()
        mock_cert.entitlement_type = CONTENT_ACCESS_CERT_TYPE
        cert_list = [mock_cert]
        self.cc.entitlement_dir = Mock()
        self.cc.entitlement_dir.list_with_content_access = Mock(return_value=cert_list)
        self.cc.entcertlib = Mock()
        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Overall Status: Disabled", cap.out)
        self.assertIn("Content Access Mode is set to Simple Content Access.", cap.out)
        self.assertIn("This host has access to content, regardless of subscription status.", cap.out)
        self.assertIn("System Purpose Status: Disabled", cap.out)

    def test_current_status_entitlement_mode(self):
        """
        Test status, when old entitlement mode is used
        """
        # Note that server sent response with "Current" status
        self.mock_entitlement_instance.get_status = Mock(return_value=MOCK_SERVICE_STATUS_ENTITLEMENT)
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({"status": "valid"})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        # There is not SCA certificate (only old entitlement)
        mock_cert = Mock()
        mock_cert.entitlement_type = "entitlement"
        cert_list = [mock_cert]
        self.cc.entitlement_dir = Mock()
        self.cc.entitlement_dir.list_with_content_access = Mock(return_value=cert_list)
        self.cc.entcertlib = Mock()
        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Overall Status: Current", cap.out)
        self.assertIn("System Purpose Status: Matched", cap.out)

    def test_status_content_access_mode_changed(self):
        """
        Test status, when old entitlement mode is used
        """
        # Note that server sent response with "Current" status
        self.mock_entitlement_instance.get_status = Mock(return_value=MOCK_SERVICE_STATUS_ENTITLEMENT)
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({"status": "valid"})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        # But entitlement directory still contain SCA certificate
        mock_cert = Mock()
        mock_cert.entitlement_type = CONTENT_ACCESS_CERT_TYPE
        cert_list = [mock_cert]
        self.cc.entitlement_dir = Mock()
        self.cc.entitlement_dir.list_with_content_access = Mock(return_value=cert_list)
        self.cc.entcertlib = Mock()
        # sub-man should be able to resurrect from this situation
        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Overall Status: Current", cap.out)
        self.assertIn("System Purpose Status: Matched", cap.out)

    def test_purpose_status_success(self):
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({"status": "valid"})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        self.cc.entcertlib = Mock()
        self.cc._determine_whether_content_access_mode_is_sca = Mock(return_value=False)
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue("System Purpose Status: Matched" in cap.out)

    def test_purpose_status_consumer_lack(self):
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({"status": "unknown"})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        self.cc.entcertlib = Mock()
        self.cc._determine_whether_content_access_mode_is_sca = Mock(return_value=False)
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue("System Purpose Status: Unknown" in cap.out)

    def test_purpose_status_consumer_no_capability(self):
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({"status": "unknown"})
        self.cc.cp._capabilities = []
        self.cc.options = Mock()
        self.cc.options.on_date = None
        self.cc.entcertlib = Mock()
        self.cc._determine_whether_content_access_mode_is_sca = Mock(return_value=False)
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue("System Purpose Status: Unknown" in cap.out)

    def test_purpose_status_mismatch(self):
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance(
            {"status": "mismatched", "reasons": ["unsatisfied usage: Production"]}
        )
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        self.cc.entcertlib = Mock()
        self.cc._determine_whether_content_access_mode_is_sca = Mock(return_value=False)
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue("System Purpose Status: Mismatched" in cap.out)
        self.assertTrue("unsatisfied usage: Production" in cap.out)
