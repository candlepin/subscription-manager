# -*- coding: utf-8 -*-

from ..test_managercli import TestCliCommand
from subscription_manager import managercli


class TestPluginsCommand(TestCliCommand):
    command_class = managercli.PluginsCommand
