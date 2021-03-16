# -*- coding: utf-8 -*-

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestOwnersCommand(TestCliProxyCommand):
    command_class = managercli.OwnersCommand

    def test_main_server_url(self):
        server_url = "https://subscription.rhsm.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])

    def test_token_(self):
        self.cc.main(["--token", "eyJhbGciOiJSUzI1NiIsInR5cCIg"])
