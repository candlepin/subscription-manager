from subscription_manager import managercli

from ..stubs import StubConsumerIdentity, StubUEP
from ..fixture import SubManFixture, Capture

from mock import Mock


class TestStatusCommand(SubManFixture):
    command_class = managercli.StatusCommand

    def setUp(self):
        super(TestStatusCommand, self).setUp()
        self.cc = self.command_class()

    def test_purpose_status_success(self):
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({'status': 'valid'})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue('System Purpose Status: Matched' in cap.out)

    def test_purpose_status_consumer_lack(self):
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({'status': 'unknown'})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue('System Purpose Status: Unknown' in cap.out)

    def test_purpose_status_consumer_no_capability(self):
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({'status': 'unknown'})
        self.cc.cp._capabilities = []
        self.cc.options = Mock()
        self.cc.options.on_date = None
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue('System Purpose Status: Unknown' in cap.out)

    def test_purpose_status_mismatch(self):
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()
        self.cc.cp.setSyspurposeCompliance({'status': 'mismatched', 'reasons': ['unsatisfied usage: Production']})
        self.cc.cp._capabilities = ["syspurpose"]
        self.cc.options = Mock()
        self.cc.options.on_date = None
        with Capture() as cap:
            self.cc._do_command()
        self.assertTrue('System Purpose Status: Mismatched' in cap.out)
        self.assertTrue('unsatisfied usage: Production' in cap.out)
