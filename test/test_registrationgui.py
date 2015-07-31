
from mock import Mock

from fixture import SubManFixture

from stubs import StubBackend, StubFacts
from subscription_manager.gui.registergui import RegisterWidget, \
    CredentialsScreen, ActivationKeyScreen, ChooseServerScreen, \
    CREDENTIALS_PAGE, CHOOSE_SERVER_PAGE

from subscription_manager.ga import GObject as ga_GObject
from subscription_manager.ga import Gtk as ga_Gtk


class RegisterWidgetTests(SubManFixture):
    def setUp(self):
        super(RegisterWidgetTests, self).setUp()
        self.backend = StubBackend()
        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': '',
                          'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict=expected_facts)

        self.rs = RegisterWidget(self.backend, self.facts)

        self.rs._screens[CHOOSE_SERVER_PAGE] = Mock()
        self.rs._screens[CHOOSE_SERVER_PAGE].index = 0
        self.rs._screens[CHOOSE_SERVER_PAGE].button_label = "Dummy"
        self.rs._screens[CHOOSE_SERVER_PAGE].apply.return_value = \
                CREDENTIALS_PAGE

    def test_show(self):
        self.rs.initialize()

    # FIXME: unit tests for gtk is a weird universe
    def test_registration_error_returns_to_page(self):
        self.rs.initialize()

        self.correct_page = None

        def error_handler(obj, msg, exc_info):
            page_after = self.rs.register_notebook.get_current_page()

            # NOTE: these exceptions are not in the nost test context,
            #       so they don't actually fail nose
            self.assertEquals(page_after, 0)
            self.correct_page = True
            self.quit()

        def emit_proceed():
            self.rs.emit('proceed')
            return False

        def emit_error():
            self.rs.emit('register-error', 'Some register error', None)
            return False

        self.rs.connect('register-error', error_handler)

        ga_GObject.timeout_add(250, self.quit)
        ga_GObject.idle_add(emit_proceed)
        ga_GObject.idle_add(emit_error)

        # run till quit or timeout
        # if we get to the state we want we can call quit
        ga_Gtk.main()

        # verify class scope self.correct_page got set correct in error handler
        self.assertTrue(self.correct_page)

    def quit(self):
        ga_Gtk.main_quit()


def mock_parent():
    parent = Mock()
    backend = StubBackend()
    parent.backend = backend
    parent.async = Mock()


class StubReg(object):
    def __init__(self):
        self.parent_window = Mock()
        self.backend = StubBackend()
        self.async = Mock()
        self.reg_info = Mock()
        self.expected_facts = {'fact1': 'one',
                               'fact2': 'two',
                               'system': '',
                               'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict=self.expected_facts)


class CredentialsScreenTests(SubManFixture):

    def setUp(self):
        super(CredentialsScreenTests, self).setUp()

        stub_reg = StubReg()
        self.screen = CredentialsScreen(reg_info=stub_reg.reg_info,
                                        async_backend=stub_reg.async,
                                        facts=stub_reg.facts,
                                        parent_window=stub_reg.parent_window)

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


class ActivationKeyScreenTests(SubManFixture):
    def setUp(self):
        super(ActivationKeyScreenTests, self).setUp()
        stub_reg = StubReg()
        self.screen = ActivationKeyScreen(reg_info=stub_reg.reg_info,
                                          async_backend=stub_reg.async,
                                          facts=stub_reg.facts,
                                          parent_window=stub_reg.parent_window)

    def test_split_activation_keys(self):
        expected = ['hello', 'world', 'how', 'are', 'you']
        key_input = "hello, world,how  are , you"
        result = self.screen._split_activation_keys(key_input)
        self.assertEquals(expected, result)


class ChooseServerScreenTests(SubManFixture):
    def setUp(self):
        super(ChooseServerScreenTests, self).setUp()
        stub_reg = StubReg()
        self.screen = ChooseServerScreen(reg_info=stub_reg.reg_info,
                                         async_backend=stub_reg.async,
                                         facts=stub_reg.facts,
                                         parent_window=stub_reg.parent_window)

    def test_activation_key_checkbox_sensitive(self):
        self.screen.server_entry.set_text("foo.bar:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))

    def test_activation_key_checkbox_prod_sensitive(self):
        self.screen.server_entry.set_text("subscription.rhn.redhat.com:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))

    def test_activation_key_checkbox_inactive_when_insensitive(self):
        self.screen.server_entry.set_text("foo.bar:443/baz")
        self.screen.activation_key_checkbox.set_active(True)
        self.screen.server_entry.set_text("subscription.rhn.redhat.com:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))
        self.assertTrue(self.screen.activation_key_checkbox.get_property('active'))
