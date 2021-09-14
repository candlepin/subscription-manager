from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestIdentityCommand(TestCliProxyCommand):
    command_class = managercli.IdentityCommand

    def test_regenerate_no_force(self):
        self.cc.main(["--regenerate"])

    def test_token_no_force(self):
        self._test_exception(["--token", "eyJhbGciOiJSUzI1NiIsInR5cCIg"])

    def test_token_with_force(self):
        self._test_no_exception(["--regenerate", "--token", "eyJhbGciOiJSUzI1NiIsInR5cCIg", "--force"])
