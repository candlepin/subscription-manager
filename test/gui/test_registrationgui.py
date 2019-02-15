from __future__ import print_function, division, absolute_import

from mock import Mock, patch

from test.fixture import SubManFixture, set_up_mock_sp_store

from test.stubs import StubBackend, StubFacts
from subscription_manager.gui.registergui import RegisterWidget, RegisterInfo,  \
    CredentialsScreen, ActivationKeyScreen, ChooseServerScreen, AsyncBackend, \
    CREDENTIALS_PAGE, CHOOSE_SERVER_PAGE
from subscription_manager.gui.autobind import AllProductsCoveredException

from subscription_manager.ga import GObject as ga_GObject
from subscription_manager.ga import Gtk as ga_Gtk

import sys
import six
from nose.plugins.attrib import attr


@attr('gui')
class RegisterWidgetTests(SubManFixture):
    def setUp(self):
        super(RegisterWidgetTests, self).setUp()
        self.exc_infos = []
        self.excs = []
        self.backend = StubBackend()
        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': '',
                          'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict=expected_facts)

        self.reg_info = RegisterInfo()
        self.rs = RegisterWidget(backend=self.backend, reg_info=self.reg_info)

        self.rs._screens[CHOOSE_SERVER_PAGE] = Mock()
        self.rs._screens[CHOOSE_SERVER_PAGE].index = 0
        self.rs._screens[CHOOSE_SERVER_PAGE].screens_index = 0
        self.rs._screens[CHOOSE_SERVER_PAGE].button_label = "Dummy"
        self.rs._screens[CHOOSE_SERVER_PAGE].apply.return_value = CREDENTIALS_PAGE

    def test_show(self):
        self.rs.initialize()

    def page_notify_handler(self, obj, param):
        page_after = obj.get_current_page()
        # NOTE: these exceptions are not in the nost test context,
        #       so they don't actually fail nose
        try:
            self.assertEqual(page_after, 0)
        except Exception:
            self.exc_infos.append(sys.exc_info())
            return

        self.correct_page = True
        self.gtk_quit()
        return False

    def error_handler(self, obj, msg, exc_info):
        page_after = self.rs.register_notebook.get_current_page()

        # NOTE: these exceptions are not in the nost test context,
        #       so they don't actually fail nose
        try:
            self.assertEqual(page_after, 0)
        except Exception:
            self.exc_infos.append(sys.exc_info())
            return

        self.correct_page = True
        self.gtk_quit()
        return False

    def emit_proceed(self):
        self.rs.emit('proceed')
        return False

    def emit_error(self):
        self.rs.emit('register-error', 'Some register error', None)
        return False

    # FIXME: unit tests for gtk is a weird universe
    def test_registration_error_returns_to_page(self):
        self.rs.initialize()

        self.correct_page = None

        self.rs.register_notebook.connect('notify::page', self.page_notify_handler)

        self.rs.connect('register-error', self.error_handler)

        ga_GObject.timeout_add(3000, self.gtk_quit_on_fail)
        ga_GObject.idle_add(self.emit_proceed)
        ga_GObject.idle_add(self.emit_error)

        # run till quit or timeout
        # if we get to the state we want we can call quit
        ga_Gtk.main()

        # If we saw any exceptions, raise them now so we fail nosetests
        for exc_info in self.exc_infos:
            six.reraise(*exc_info)

        self.assertTrue(self.correct_page)

    # if we got the right answer, go ahead and end gtk.main()
    def gtk_quit(self):
        ga_Gtk.main_quit()

    # End the main loop, but first add an exception to sys.exc_info so
    # the end of the tests can fail on it.
    def gtk_quit_on_fail(self):
        try:
            self.fail("registergui didn't get a signal before the timeout.")
        except Exception:
            self.exc_infos.append(sys.exc_info())

        ga_Gtk.main_quit()

    def test_screen_history_empty(self):
        self.rs.initialize()
        self.assertTrue(self.rs.applied_screen_history.is_empty())
        self.rs.apply_current_screen()
        self.assertFalse(self.rs.applied_screen_history.is_empty())
        self.rs._pop_last_screen()
        self.assertTrue(self.rs.applied_screen_history.is_empty())


def mock_parent():
    parent = Mock()
    backend = StubBackend()
    parent.backend = backend
    parent.async_backend = Mock()


class StubReg(object):
    def __init__(self):
        self.parent_window = Mock()
        self.backend = StubBackend()
        self.async_backend = Mock()
        self.reg_info = Mock()
        self.expected_facts = {'fact1': 'one',
                               'fact2': 'two',
                               'system': '',
                               'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict=self.expected_facts)


@attr('gui')
class CredentialsScreenTests(SubManFixture):

    def setUp(self):
        super(CredentialsScreenTests, self).setUp()

        stub_reg = StubReg()
        self.screen = CredentialsScreen(reg_info=stub_reg.reg_info,
                                        async_backend=stub_reg.async_backend,
                                        parent_window=stub_reg.parent_window)

    def test_clear_credentials_dialog(self):
        # Pull initial value here since it will be different per machine.
        default_consumer_name_value = self.screen.consumer_name.get_text()
        self.screen.account_login.set_text("foo")
        self.screen.account_password.set_text("bar")
        self.screen.skip_auto_bind.set_active(True)
        self.screen.consumer_name.set_text("CONSUMER")
        self.screen.clear()
        self.assertEqual("", self.screen.account_login.get_text())
        self.assertEqual("", self.screen.account_password.get_text())
        self.assertFalse(self.screen.skip_auto_bind.get_active())
        self.assertEqual(default_consumer_name_value,
                          self.screen.consumer_name.get_text())


@attr('gui')
class ActivationKeyScreenTests(SubManFixture):
    def setUp(self):
        super(ActivationKeyScreenTests, self).setUp()
        stub_reg = StubReg()
        self.screen = ActivationKeyScreen(reg_info=stub_reg.reg_info,
                                          async_backend=stub_reg.async_backend,
                                          parent_window=stub_reg.parent_window)

    def test_split_activation_keys(self):
        expected = ['hello', 'world', 'how', 'are', 'you']
        key_input = "hello, world,how  are , you"
        result = self.screen._split_activation_keys(key_input)
        self.assertEqual(expected, result)


@attr('gui')
class ChooseServerScreenTests(SubManFixture):
    def setUp(self):
        super(ChooseServerScreenTests, self).setUp()
        stub_reg = StubReg()
        self.screen = ChooseServerScreen(reg_info=stub_reg.reg_info,
                                         async_backend=stub_reg.async_backend,
                                         parent_window=stub_reg.parent_window)

    def test_activation_key_checkbox_sensitive(self):
        self.screen.server_entry.set_text("foo.bar:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))

    def test_activation_key_checkbox_prod_sensitive(self):
        self.screen.server_entry.set_text("subscription.rhsm.redhat.com:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))

    def test_activation_key_checkbox_inactive_when_insensitive(self):
        self.screen.server_entry.set_text("foo.bar:443/baz")
        self.screen.activation_key_checkbox.set_active(True)
        self.screen.server_entry.set_text("subscription.rhsm.redhat.com:443/baz")
        self.assertTrue(self.screen.activation_key_checkbox.get_property('sensitive'))
        self.assertTrue(self.screen.activation_key_checkbox.get_property('active'))

    @patch('subscription_manager.gui.registergui.config')
    def test__on_default_button_clicked(self, config):
        config.DEFAULT_HOSTNAME = "subscription.rhsm.redhat.com"
        config.DEFAULT_PORT = '443'
        config.DEFAULT_PREFIX = "/subscription"

        non_default = "foo.bar:8443/baz"
        expected = "%s:%s%s" % (config.DEFAULT_HOSTNAME,
            config.DEFAULT_PORT,
            config.DEFAULT_PREFIX)
        self.screen.server_entry.set_text(non_default)
        self.screen._on_default_button_clicked(None)  # The widget param is not used
        result = self.screen.server_entry.get_text()
        self.assertEqual(expected, result)


@attr('gui')
class AsyncBackendTests(SubManFixture):
    def setUp(self):
        super(AsyncBackendTests, self).setUp()
        self.backend = StubBackend()
        self.asyncBackend = AsyncBackend(self.backend)
        syspurpose_patch = patch('subscription_manager.syspurposelib.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

    def test_auto_system_complete(self):
        self.backend.cp_provider.get_consumer_auth_cp().getConsumer = \
            Mock(return_value={"serviceLevel": "", "owner": {"key": "admin"}})
        self.backend.cs.valid_products = ['RH001', 'RH002']
        self.backend.cs.installed_products = ['RH001', 'RH002']
        self.backend.cs.partial_stacks = []
        self.backend.cs.system_status = 'valid'
        self.backend.cp_provider.get_consumer_auth_cp().getServiceLevelList = Mock(return_value=[])
        self.assertRaises(AllProductsCoveredException, self.asyncBackend._find_suitable_subscriptions, '12345')

    def test_auto_system_partial(self):
        self.backend.cp_provider.get_consumer_auth_cp().getConsumer = \
            Mock(return_value={"serviceLevel": "", "owner": {"key": "admin"}})
        self.backend.cp_provider.get_consumer_auth_cp().dryRunBind = Mock(return_value=[])
        self.backend.cs.valid_products = ['RH001', 'RH002']
        self.backend.cs.installed_products = ['RH001', 'RH002']
        self.backend.cs.partial_stacks = []
        self.backend.cs.system_status = 'partial'
        self.backend.cp_provider.get_consumer_auth_cp().getServiceLevelList = Mock(return_value=[])
        self.asyncBackend._find_suitable_subscriptions('12345')
