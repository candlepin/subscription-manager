from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestIdentityCommand(TestCliProxyCommand):
    command_class = managercli.IdentityCommand

    def test_regenerate_no_force(self):
        self.cc.main(["--regenerate"])
