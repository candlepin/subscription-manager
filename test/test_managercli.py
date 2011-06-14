import unittest
import sys

from subscription_manager import managercli
from stubs import MockStdout, MockStderr


class TestCliCommand(unittest.TestCase):
    command_class = managercli.CliCommand

    def setUp(self):
        self.cc = self.command_class()
        # neuter the _do_command, since this is mostly
        # for testing arg parsing
        self.cc._do_command = self._do_command
        self.cc.assert_should_be_registered = self._asert_should_be_registered

        # stub out uep
        managercli.connection.UEPConnection = self._uep_connection
        sys.stdout = MockStdout()
        sys.stderr = MockStderr()

    def tearDown(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def _uep_connection(self, *args, **kwargs):
        pass

    def _do_command(self):
        pass

    def _asert_should_be_registered(self):
        pass

    def test_main_no_args(self):
        try:
            self.cc.main()
        except SystemExit, e:
            # 2 == no args given
            self.assertEquals(e.code, 2)

    def test_main_debug_no_args(self):
        try:
            self.cc.main(["--debug"])
        except SystemExit, e:
            # 2 == no args given
            self.assertEquals(e.code, 2)

    def test_main_debug_10(self):
        self.cc.main(["--debug", "10"])
        self.assertEquals('10', self.cc.options.debug)
        self.assertEquals(type('10'), type(self.cc.options.debug))

    def _main_help(self, args):
        mstdout = MockStdout()
        sys.stdout = mstdout
        try:
            self.cc.main(args)
        except SystemExit, e:
            # --help/-h returns 0
            self.assertEquals(e.code, 0)
        sys.stdout = sys.__stdout__
        # I could test for strings here, but that
        # would break if we run tests in a locale/lang
        assert len(mstdout.buffer) > 0

    def test_main_short_help(self):
        self._main_help(["-h"])

    def test_main_long_help(self):
        self._main_help(["--help"])


# for command classes that expect proxy related cli args
class TestCliProxyCommand(TestCliCommand):
    def test_main_proxy_url(self):
        proxy_host = "example.com"
        proxy_port = "3128"
        proxy_url = "%s:%s" % (proxy_host, proxy_port)
        self.cc.main(["--proxy", proxy_url])
        self.assertEquals(proxy_url, self.cc.options.proxy_url)
        self.assertEquals(type(proxy_url), type(self.cc.options.proxy_url))
        self.assertEquals(proxy_host, self.cc.proxy_hostname)
        self.assertEquals(proxy_port, self.cc.proxy_port)

    def test_main_proxy_user(self):
        proxy_user = "buster"
        self.cc.main(["--proxyuser", proxy_user])
        self.assertEquals(proxy_user, self.cc.proxy_user)

    def test_main_proxy_password(self):
        proxy_password = "nomoresecrets"
        self.cc.main(["--proxypassword", proxy_password])
        self.assertEquals(proxy_password, self.cc.proxy_password)


class TestCleanCommand(TestCliCommand):
    command_class = managercli.CleanCommand


class TestRefreshCommand(TestCliProxyCommand):
    command_class = managercli.RefreshCommand


class TestIdentityCommand(TestCliProxyCommand):

    command_class = managercli.IdentityCommand

    def test_regenerate_no_force(self):
        self.cc.main(["--regenerate"])


class TestRegisterCommand(TestCliProxyCommand):
    command_class = managercli.RegisterCommand


class TestUnRegisterCommand(TestCliProxyCommand):
    command_class = managercli.UnRegisterCommand


class TestActivateCommand(TestCliProxyCommand):
    command_class = managercli.ActivateCommand


class TestSubscribeCommand(TestCliProxyCommand):
    command_class = managercli.SubscribeCommand


class TestUnSubscribeCommand(TestCliProxyCommand):
    command_class = managercli.UnSubscribeCommand


class TestFactsCommand(TestCliProxyCommand):
    command_class = managercli.FactsCommand
