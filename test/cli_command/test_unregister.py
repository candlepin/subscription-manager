from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestUnRegisterCommand(TestCliProxyCommand):
    command_class = managercli.UnRegisterCommand
