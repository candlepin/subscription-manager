from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestRedeemCommand(TestCliProxyCommand):
    command_class = managercli.RedeemCommand
