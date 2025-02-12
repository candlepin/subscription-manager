from subscription_manager import managercli

from ..stubs import StubIdentity
from ..fixture import SubManFixture, Capture

from unittest.mock import Mock

from subscription_manager import injection as inj


class TestStatusCommand(SubManFixture):
    command_class = managercli.StatusCommand

    def setUp(self):
        super(TestStatusCommand, self).setUp()
        self.cc = self.command_class()

    def test_status_registered(self):
        """
        Test status, when the system is registered
        """
        self.cc.options = Mock()
        self.cc.options.on_date = None
        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Overall Status: Registered", cap.out)

    def test_status_unregistered(self):
        """
        Test status, when the system is not registered
        """
        inj.provide(inj.IDENTITY, StubIdentity())
        self.cc.options = Mock()
        self.cc.options.on_date = None
        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Overall Status: Not registered", cap.out)
