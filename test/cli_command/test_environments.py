from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli

from ..stubs import StubUEP


class TestEnvironmentsCommand(TestCliProxyCommand):
    command_class = managercli.EnvironmentsCommand

    def test_main_server_url(self):
        server_url = "https://subscription.rhsm.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])

    def test_library_no_longer_filtered(self):
        self.cc.cp = StubUEP()
        environments = []
        environments.append({'name': 'JarJar'})
        environments.append({'name': 'Library'})
        environments.append({'name': 'library'})
        environments.append({'name': 'Binks'})
        self.cc.cp.setEnvironmentList(environments)
        results = self.cc._get_environments("Anikan")
        self.assertTrue(len(results) == 4)
