import sys
import unittest

from mock import Mock
from stubs import StubUEP, StubEntitlementCertificate, StubCertificateDirectory, StubProduct, StubBackend, StubFacts
from subscription_manager.gui.registergui import RegisterScreen


class RegisterScreenTests(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.consumer = Mock()
        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': '',
                          'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict = expected_facts)

        self.rs = RegisterScreen(self.backend, self.consumer, self.facts)

    def test_show(self):
        self.rs.show()

    def test_register(self):
        self.rs.uname.set_text("foo")
        self.rs.passwd.set_text("bar")
        self.rs.register()

#    def test_enviroment_selected(self):
#        self.rs._environment_selected()
