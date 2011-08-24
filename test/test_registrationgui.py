import sys
import unittest

from mock import Mock
from stubs import StubUEP, StubEntitlementCertificate, StubCertificateDirectory, StubProduct, StubBackend, StubFacts
from subscription_manager.gui.registergui import RegisterScreen, CREDENTIALS_PAGE, OWNER_SELECT_PAGE


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

    def test_cancel_registration_returns_to_credentials_screen(self):
        self.rs.uname.set_text("foo")
        self.rs.passwd.set_text("bar")
        self.rs.register()
        self.assertNotEquals(CREDENTIALS_PAGE, self.rs.register_notebook.get_current_page())
        self.rs.cancel(self.rs.cancel_button)
        self.assertEquals(CREDENTIALS_PAGE, self.rs.register_notebook.get_current_page())
