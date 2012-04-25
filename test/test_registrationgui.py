import unittest

from mock import Mock
from stubs import StubBackend, StubFacts
from subscription_manager.gui.registergui import RegisterScreen, \
        CREDENTIALS_PAGE


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

    def test_show_registration_returns_to_credentials_screen(self):
        self.rs.uname.set_text("foo")
        self.rs.passwd.set_text("bar")
        self.rs.register()
        self.assertNotEquals(CREDENTIALS_PAGE, self.rs.register_notebook.get_current_page())
        self.rs.cancel(self.rs.cancel_button)
        self.assertNotEquals(CREDENTIALS_PAGE, self.rs.register_notebook.get_current_page())
        self.rs.show()
        self.assertEquals(CREDENTIALS_PAGE, self.rs.register_notebook.get_current_page())

    def test_clear_credentials_dialog(self):
        # Pull initial value here since it will be different per machine.
        default_consumer_name_value = self.rs.consumer_name.get_text()
        self.rs.uname.set_text("foo")
        self.rs.passwd.set_text("bar")
        self.rs.skip_auto_bind.set_active(True)
        self.rs.consumer_name.set_text("CONSUMER")
        self.rs._clear_registration_widgets()
        self.assertEquals("", self.rs.uname.get_text())
        self.assertEquals("", self.rs.passwd.get_text())
        self.assertFalse(self.rs.skip_auto_bind.get_active())
        self.assertEquals(default_consumer_name_value, self.rs.consumer_name.get_text())
