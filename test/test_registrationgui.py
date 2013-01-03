import unittest

from mock import Mock

import rhsm_display
rhsm_display.set_display()

from stubs import StubBackend, StubFacts
from subscription_manager.gui.registergui import RegisterScreen, \
        CredentialsScreen, ActivationKeyScreen, ChooseServerScreen, \
        CREDENTIALS_PAGE, CHOOSE_SERVER_PAGE


class RegisterScreenTests(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.consumer = Mock()
        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': '',
                          'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict=expected_facts)

        self.rs = RegisterScreen(self.backend, self.consumer, self.facts)

        self.rs._screens[CHOOSE_SERVER_PAGE] = Mock()
        self.rs._screens[CHOOSE_SERVER_PAGE].index = 0
        self.rs._screens[CHOOSE_SERVER_PAGE].button_label = "Dummy"
        self.rs._screens[CHOOSE_SERVER_PAGE].apply.return_value = \
                CREDENTIALS_PAGE

    def test_show(self):
        self.rs.show()

    def test_show_registration_returns_to_choose_server_screen(self):
        self.rs.show()
        self.rs.register()
        self.assertEquals(CREDENTIALS_PAGE,
                          self.rs.register_notebook.get_current_page() - 1)
        self.rs.cancel(self.rs.cancel_button)
        self.rs.show()
        self.assertEquals(CHOOSE_SERVER_PAGE,
                          self.rs.register_notebook.get_current_page())


class CredentialsScreenTests(unittest.TestCase):

    def setUp(self):
        self.backend = StubBackend()
        self.parent = Mock()

        self.screen = CredentialsScreen(self.backend, self.parent)

    def test_clear_credentials_dialog(self):
        # Pull initial value here since it will be different per machine.
        default_consumer_name_value = self.screen.consumer_name.get_text()
        self.screen.account_login.set_text("foo")
        self.screen.account_password.set_text("bar")
        self.screen.skip_auto_bind.set_active(True)
        self.screen.consumer_name.set_text("CONSUMER")
        self.screen.clear()
        self.assertEquals("", self.screen.account_login.get_text())
        self.assertEquals("", self.screen.account_password.get_text())
        self.assertFalse(self.screen.skip_auto_bind.get_active())
        self.assertEquals(default_consumer_name_value,
                          self.screen.consumer_name.get_text())


class ActivationKeyScreenTests(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.parent = Mock()
        self.screen = ActivationKeyScreen(self.backend, self.parent)

    def test_split_activation_keys(self):
        expected = ['hello', 'world', 'how', 'are', 'you']
        input = "hello, world,how  are , you"
        result = self.screen._split_activation_keys(input)
        self.assertEquals(expected, result)


class ChooseServerScreenTests(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.parent = Mock()
        self.screen = ChooseServerScreen(self.backend, self.parent)

    def test_activation_key_checkbox_sensitive(self):
        self.screen.server_entry.set_text("foo.bar:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))

    def test_activation_key_checkbox_insensitive(self):
        self.screen.server_entry.set_text("subscription.rhn.redhat.com:443/baz")
        self.assertFalse(self.screen.activation_key_checkbox.get_property('sensitive'))

    def test_activation_key_checkbox_inactive_when_insensitive(self):
        self.screen.server_entry.set_text("foo.bar:443/baz")
        self.screen.activation_key_checkbox.set_active(True)
        self.screen.server_entry.set_text("subscription.rhn.redhat.com:443/baz")
        self.assertFalse(self.screen.activation_key_checkbox.get_property('sensitive'))
        self.assertFalse(self.screen.activation_key_checkbox.get_property('active'))
