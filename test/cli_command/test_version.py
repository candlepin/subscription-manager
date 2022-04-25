from ..test_managercli import TestCliCommand
from subscription_manager import managercli


class TestVersionCommand(TestCliCommand):
    command_class = managercli.VersionCommand
