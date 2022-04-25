from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestFactsCommand(TestCliProxyCommand):
    command_class = managercli.FactsCommand
