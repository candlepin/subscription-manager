# -*- coding: utf-8 -*-

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestRefreshCommand(TestCliProxyCommand):
    command_class = managercli.RefreshCommand

    def test_force_option(self):
        self.cc.main(["--force"])
