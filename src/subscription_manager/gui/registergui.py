#
# Registration dialog/wizard
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import socket
import logging
import threading
import Queue

import gobject
import gtk
import gtk.glade

from subscription_manager import managerlib
import rhsm.config as config
from subscription_manager.branding import get_branding
from subscription_manager.cache import ProfileManager, InstalledProductsManager
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.utils import parse_server_info, ServerUrlParseError,\
        is_valid_server_info, MissingCaCertException
from subscription_manager.gui import networkConfig
from subscription_manager.gui import widgets

from subscription_manager.gui.utils import handle_gui_exception, errorWindow
from subscription_manager.gui.autobind import DryRunResult, \
        ServiceLevelNotSupportedException, AllProductsCoveredException, \
        NoProductsException
from subscription_manager.gui.messageWindow import InfoDialog, OkDialog

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("rhsm")
gtk.glade.textdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)
CFG = config.initConfig()

# An implied Katello environment which we can't actual register to.
LIBRARY_ENV_NAME = "library"

DONT_CHANGE = -2
PROGRESS_PAGE = -1
CHOOSE_SERVER_PAGE = 0
CREDENTIALS_PAGE = 1
OWNER_SELECT_PAGE = 2
ENVIRONMENT_SELECT_PAGE = 3
PERFORM_REGISTER_PAGE = 4
SELECT_SLA_PAGE = 5
CONFIRM_SUBS_PAGE = 6
PERFORM_SUBSCRIBE_PAGE = 7
FINISH = 100

REGISTER_ERROR = _("<b>Unable to register the system.</b>") + \
    "\n%s\n" + \
    _("Please see /var/log/rhsm/rhsm.log for more information.")


class RegisterScreen(widgets.GladeWidget):
    """
      Registration Widget Screen
    """
    widget_names = ['register_dialog', 'register_notebook',
                    'register_progressbar', 'register_details_label',
                    'cancel_button', 'register_button']

    def __init__(self, backend, consumer, facts=None, callbacks=[]):
        """
        Callbacks will be executed when registration status changes.
        """

        widgets.GladeWidget.__init__(self, "registration.glade")

        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.callbacks = callbacks

        self.async = AsyncBackend(self.backend)

        dic = {"on_register_cancel_button_clicked": self.cancel,
               "on_register_button_clicked": self._on_register_button_clicked,
               "hide": self.cancel,
               "delete_event": self._delete_event,
            }
        self.glade.signal_autoconnect(dic)

        self.window = self.register_dialog
        screen_classes = [ChooseServerScreen, CredentialsScreen,
                          OrganizationScreen, EnvironmentScreen,
                          PerformRegisterScreen, SelectSLAScreen,
                          ConfirmSubscriptionsScreen, PerformSubscribeScreen]
        self._screens = []
        for screen_class in screen_classes:
            screen = screen_class(self, self.backend)
            self._screens.append(screen)
            if screen.needs_gui:
                screen.index = self.register_notebook.append_page(
                        screen.container)

        self._current_screen = CHOOSE_SERVER_PAGE

        # values that will be set by the screens
        self.username = None
        self.consumername = None
        self.owner_key = None
        self.environment = None
        self.current_sla = None
        self.dry_run_result = None
        self.skip_auto_bind = False

        # XXX needed by firstboot
        self.password = None

    def show(self):
        # Ensure that we start on the first page and that
        # all widgets are cleared.
        self._set_screen(CHOOSE_SERVER_PAGE)

        self._set_navigation_sensitive(True)
        self._clear_registration_widgets()
        self.timer = gobject.timeout_add(100, self._timeout_callback)
        self.register_dialog.show()

    def _set_navigation_sensitive(self, sensitive):
        self.cancel_button.set_sensitive(sensitive)
        self.register_button.set_sensitive(sensitive)

    def _set_screen(self, screen):
        if screen > PROGRESS_PAGE:
            self._current_screen = screen
            if self._screens[screen].needs_gui:
                self._set_register_label(screen)
                self.register_notebook.set_current_page(self._screens[screen].index)
        else:
            self.register_notebook.set_current_page(screen + 1)

    def _set_register_label(self, screen):
        button_label = self._screens[screen].button_label
        self.register_button.set_label(button_label)

    def _delete_event(self, event, data=None):
        return self.close_window()

    def cancel(self, button):
        self.close_window()

    # callback needs the extra arg, so just a wrapper here
    def _on_register_button_clicked(self, button):
        self.register()

    def register(self):
        result = self._screens[self._current_screen].apply()

        if result == FINISH:
            self.finish_registration()
            return True
        elif result == DONT_CHANGE:
            return False

        self._screens[self._current_screen].post()

        self._run_pre(result)
        return False

    def _run_pre(self, screen):
        # XXX move this into the button handling somehow?
        if screen == FINISH:
            self.finish_registration()
            return

        self._set_screen(screen)
        async = self._screens[self._current_screen].pre()
        if async:
            self._set_navigation_sensitive(False)
            self._set_screen(PROGRESS_PAGE)
            self._set_register_details_label(
                    self._screens[self._current_screen].pre_message)

    def _timeout_callback(self):
        self.register_progressbar.pulse()
        # return true to keep it pulsing
        return True

    def finish_registration(self, failed=False):
        # failed is used by the firstboot subclasses to decide if they should
        # advance the screen or not.
        # XXX it would be cool here to do some async spinning while the
        # main window gui refreshes itself

        self.close_window()

        self.emit_consumer_signal()

        gobject.source_remove(self.timer)

    def emit_consumer_signal(self):
        for method in self.callbacks:
            method()

    def close_window(self):
        self.register_dialog.hide()
        return True

    def set_parent_window(self, window):
        self.register_dialog.set_transient_for(window)

    def _set_register_details_label(self, details):
        self.register_details_label.set_label("<small>%s</small>" % details)

    def _clear_registration_widgets(self):
        for screen in self._screens:
            screen.clear()

    def pre_done(self, next_screen):
        self._set_navigation_sensitive(True)
        if next_screen == DONT_CHANGE:
            self._set_screen(self._current_screen)
        else:
            self._screens[self._current_screen].post()
            self._run_pre(next_screen)


class AutobindWizard(RegisterScreen):

    def __init__(self, backend, consumer, facts):
        super(AutobindWizard, self).__init__(backend, consumer, facts)

    def show(self):
        super(AutobindWizard, self).show()
        self._run_pre(SELECT_SLA_PAGE)


class Screen(widgets.GladeWidget):
    widget_names = widgets.GladeWidget.widget_names + ['container']

    def __init__(self, glade_file, parent, backend):
        super(Screen, self).__init__(glade_file)

        self.pre_message = ""
        self.button_label = _("Register")
        self.needs_gui = True
        self.index = -1
        self._parent = parent
        self._backend = backend

    def pre(self):
        return False

    def apply(self):
        pass

    def post(self):
        pass

    def clear(self):
        pass


class NoGuiScreen(object):

    def __init__(self, parent, backend):
        self._parent = parent
        self._backend = backend
        self.button_label = None
        self.needs_gui = False

    def pre(self):
        return True

    def apply(self):
        pass

    def post(self):
        pass

    def clear(self):
        pass


class PerformRegisterScreen(NoGuiScreen):

    def __init__(self, parent, backend):
        super(PerformRegisterScreen, self).__init__(parent, backend)
        self.pre_message = _("Registering your system")

    def _on_registration_finished_cb(self, new_account, error=None):
        try:
            if error != None:
                raise error

            managerlib.persist_consumer_cert(new_account)
            self._parent.consumer.reload()
            if self._parent.skip_auto_bind:
                self._parent.pre_done(FINISH)
            else:
                self._parent.pre_done(SELECT_SLA_PAGE)

        except Exception, e:
            handle_gui_exception(e, REGISTER_ERROR, self._parent.window)
            self._parent.finish_registration(failed=True)

    def pre(self):
        log.info("Registering to owner: %s environment: %s" \
                % (self._parent.owner_key, self._parent.environment))

        self._parent.async.register_consumer(self._parent.consumername,
                                             self._parent.facts,
                                             self._parent.owner_key,
                                             self._parent.environment,
                                             self._on_registration_finished_cb)

        return True


class PerformSubscribeScreen(NoGuiScreen):

    def __init__(self, parent, backend):
        super(PerformSubscribeScreen, self).__init__(parent, backend)
        self.pre_message = _("Subscribing to entitlements")

    def _on_subscribing_finished_cb(self, unused, error=None):
        try:
            if error != None:
                raise error
            self._parent.pre_done(FINISH)

        except Exception, e:
            handle_gui_exception(e, _("Error subscribing: %s"),
                                 self._parent.window)
            self._parent.finish_registration(failed=True)

    def pre(self):
        self._parent.async.subscribe(self._parent.consumer.getConsumerId(),
                                     self._parent.current_sla,
                                     self._parent.dry_run_result,
                                     self._on_subscribing_finished_cb)

        return True


class ConfirmSubscriptionsScreen(Screen):
    """ Confirm Subscriptions GUI Window """

    widget_names = Screen.widget_names + ['subs_treeview', 'back_button',
                                          'sla_label']

    def __init__(self, parent, backend):

        super(ConfirmSubscriptionsScreen, self).__init__("confirmsubs.glade",
                                                         parent,
                                                         backend)
        self.button_label = _("Subscribe")

        self.store = gtk.ListStore(str)
        # For now just going to set up one product name column, we will need
        # to display more information though.
        self.subs_treeview.set_model(self.store)
        column = gtk.TreeViewColumn(_("Subscription"))
        self.subs_treeview.append_column(column)
        # create a CellRendererText to render the data
        self.cell = gtk.CellRendererText()
        column.pack_start(self.cell, True)
        column.add_attribute(self.cell, 'text', 0)
        column.set_sort_column_id(0)
        self.subs_treeview.set_search_column(0)

    def apply(self):
        return PERFORM_SUBSCRIBE_PAGE

    def set_model(self):
        self._dry_run_result = self._parent.dry_run_result

        # Make sure that the store is cleared each time
        # the data is loaded into the screen.
        self.store.clear()
        log.info("Using service level: %s" % self._dry_run_result.service_level)
        self.sla_label.set_markup("<b>" + self._dry_run_result.service_level + \
                "</b>")

        for pool_quantity in self._dry_run_result.json:
            self.store.append([pool_quantity['pool']['productName']])

    def pre(self):
        self.set_model()
        return False


class SelectSLAScreen(Screen):
    """
    An wizard screen that displays the available
    SLAs that are provided by the installed products.
    """
    widget_names = Screen.widget_names + ['product_list_label',
                                          'sla_radio_container',
                                          'owner_treeview']

    def __init__(self, parent, backend):
        super(SelectSLAScreen, self).__init__("selectsla.glade",
                                               parent, backend)

        self.pre_message = _("Finding suitable service levels")
        self.button_label = _("Next")

        self._dry_run_result = None

    def set_model(self, unentitled_prod_certs, sla_data_map):
        self.product_list_label.set_text(
                self._format_prods(unentitled_prod_certs))
        group = None
        # reverse iterate the list as that will most likely put 'None' last.
        # then pack_start so we don't end up with radio buttons at the bottom
        # of the screen.
        for sla in reversed(sla_data_map.keys()):
            radio = gtk.RadioButton(group=group, label=sla)
            radio.connect("toggled", self._radio_clicked, sla)
            self.sla_radio_container.pack_start(radio, expand=False, fill=False)
            radio.show()
            group = radio

        # set the initial radio button as default selection.
        group.set_active(True)

    def apply(self):
        return CONFIRM_SUBS_PAGE

    def post(self):
        self._parent.dry_run_result = self._dry_run_result

    def clear(self):
        child_widgets = self.sla_radio_container.get_children()
        for child in child_widgets:
            self.sla_radio_container.remove(child)

    def _radio_clicked(self, button, service_level):
        if button.get_active():
            self._dry_run_result = self._sla_data_map[service_level]

    def _format_prods(self, prod_certs):
        prod_str = ""
        for i, cert in enumerate(prod_certs):
            log.debug(cert)
            prod_str = "%s%s" % (prod_str, cert.products[0].name)
            if i + 1 < len(prod_certs):
                prod_str += ", "
        return prod_str

    def _on_get_service_levels_cb(self, result, error=None):
        if error != None:
            if isinstance(error, ServiceLevelNotSupportedException):
                OkDialog(_("Unable to auto-subscribe, server does not support service levels."),
                        parent=self._parent.window)
            elif isinstance(error, NoProductsException):
                InfoDialog(_("No installed products on system. No need to update certificates at this time."),
                           parent=self._parent.window)
            elif isinstance(error, AllProductsCoveredException):
                InfoDialog(_("All installed products are covered by valid entitlements. No need to update certificates at this time."),
                           parent=self._parent.window)
            else:
                handle_gui_exception(error, _("Error subscribing"),
                                     self._parent.window)
            self._parent.finish_registration(failed=True)
            return

        (current_sla, unentitled_products, sla_data_map) = result

        self._parent.current_sla = current_sla
        if len(sla_data_map) == 1:
            # If system already had a service level, we can hit this point
            # when we cannot fix any unentitled products:
            if current_sla is not None and \
                    not self._can_add_more_subs(current_sla, sla_data_map):
                handle_gui_exception(None,
                                     _("Unable to subscribe to any additional "
                                     "products at current service level: %s. "
                                     "Please use the \"All Available "
                                     "Subscriptions\" tab to manually "
                                     "entitle this system.") % current_sla,
                                    self._parent.window)
                self._parent.finish_registration(failed=True)
                return

            self._dry_run_result = sla_data_map.values()[0]
            self._parent.pre_done(CONFIRM_SUBS_PAGE)
        elif len(sla_data_map) > 1:
            self._sla_data_map = sla_data_map
            self.set_model(unentitled_products, sla_data_map)
            self._parent.pre_done(DONT_CHANGE)
        else:
            log.info("No suitable service levels found.")
            handle_gui_exception(None,
                                 _("No service levels will cover all installed "
                                 "products. Please use the \"All Available "
                                 "Subscriptions\" tab to manually entitle "
                                 "this system."), parent=self._parent.window)
            self._parent.finish_registration(failed=True)

    def pre(self):
        self._parent.async.find_service_levels(self._parent.consumer,
                                               self._parent.facts,
                                               self._on_get_service_levels_cb)
        return True

    def _can_add_more_subs(self, current_sla, sla_data_map):
        """
        Check if a system that already has a selected sla can get more
        entitlements at their sla level
        """
        if current_sla is not None:
            result = sla_data_map[current_sla]
            return len(result.json) > 0
        return False


class EnvironmentScreen(Screen):
    widget_names = Screen.widget_names + ['environment_treeview']

    def __init__(self, parent, backend):
        super(EnvironmentScreen, self).__init__("environment.glade",
                                                 parent, backend)

        self.pre_message = _("Fetching list of possible environments")
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Environment"), renderer, text=1)
        self.environment_treeview.set_property("headers-visible", False)
        self.environment_treeview.append_column(column)

    def _on_get_environment_list_cb(self, result_tuple, error=None):
        environments = result_tuple
        if error != None:
            handle_gui_exception(error, REGISTER_ERROR, self._parent.window)
            self._parent.finish_registration(failed=True)
            return

        if not environments:
            self._environment = None
            self._parent.pre_done(PERFORM_REGISTER_PAGE)
            return

        envs = [(env['id'], env['name']) for env in environments]
        if len(envs) == 1:
            self._environment = envs[0][0]
            self._parent.pre_done(PERFORM_REGISTER_PAGE)
        else:
            self.set_model(envs)
            self._parent.pre_done(DONT_CHANGE)

    def pre(self):
        self._parent.async.get_environment_list(self._parent.owner_key,
                                                self._on_get_environment_list_cb)
        return True

    def apply(self):
        model, tree_iter = self.environment_treeview.get_selection().get_selected()
        self._environment = model.get_value(tree_iter, 0)
        return PERFORM_REGISTER_PAGE

    def post(self):
        self._parent.environment = self._environment

    def set_model(self, envs):
        environment_model = gtk.ListStore(str, str)
        for env in envs:
            environment_model.append(env)

        self.environment_treeview.set_model(environment_model)

        self.environment_treeview.get_selection().select_iter(
                environment_model.get_iter_first())


class OrganizationScreen(Screen):
    widget_names = Screen.widget_names + ['owner_treeview']

    def __init__(self, parent, backend):
        super(OrganizationScreen, self).__init__("organization.glade",
                                                  parent, backend)

        self.pre_message = _("Fetching list of possible organizations")

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Organization"), renderer, text=1)
        self.owner_treeview.set_property("headers-visible", False)
        self.owner_treeview.append_column(column)

        self._owner_key = None

    def _on_get_owner_list_cb(self, owners, error=None):
        if error != None:
            handle_gui_exception(error, REGISTER_ERROR,
                    self._parent.window)
            self._parent.pre_done(CREDENTIALS_PAGE)
            return

        owners = [(owner['key'], owner['displayName']) for owner in owners]

        if len(owners) == 0:
            handle_gui_exception(None,
                    _("<b>User %s is not able to register with any orgs.</b>") \
                            % (self._parent.username),
                    self._parent.window)
            self._parent.finish_registration(failed=True)
            return

        if len(owners) == 1:
            self._owner_key = owners[0][0]
            self._parent.pre_done(ENVIRONMENT_SELECT_PAGE)
        else:
            self.set_model(owners)
            self._parent.pre_done(DONT_CHANGE)

    def pre(self):
        self._parent.async.get_owner_list(self._parent.username,
                                          self._on_get_owner_list_cb)
        return True

    def apply(self):
        model, tree_iter = self.owner_treeview.get_selection().get_selected()
        self._owner_key = model.get_value(tree_iter, 0)
        return ENVIRONMENT_SELECT_PAGE

    def post(self):
        self._parent.owner_key = self._owner_key

    def set_model(self, owners):
        owner_model = gtk.ListStore(str, str)
        for owner in owners:
            owner_model.append(owner)

        self.owner_treeview.set_model(owner_model)

        self.owner_treeview.get_selection().select_iter(
                owner_model.get_iter_first())


class CredentialsScreen(Screen):
    widget_names = Screen.widget_names + ['skip_auto_bind', 'consumer_name',
                                          'account_login', 'account_password']

    def __init__(self, parent, backend):
        super(CredentialsScreen, self).__init__("credentials.glade",
                                                 parent, backend)

        self._initialize_consumer_name()

        register_tip_label = self.glade.get_widget("registration_tip_label")
        register_tip_label.set_label("<small>%s</small>" % \
                get_branding().GUI_FORGOT_LOGIN_TIP)

        register_header_label = \
                self.glade.get_widget("registration_header_label")
        register_header_label.set_label("<b>%s</b>" % \
                get_branding().GUI_REGISTRATION_HEADER)

    def _initialize_consumer_name(self):
        if not self.consumer_name.get_text():
            self.consumer_name.set_text(socket.gethostname())

    def _validate_consumername(self, consumername):
        if not consumername:
            errorWindow(_("You must enter a system name."), self._parent.window)
            self.consumer_name.grab_focus()
            return False
        return True

    def _validate_account(self):
        # validate / check user name
        if self.account_login.get_text().strip() == "":
            errorWindow(_("You must enter a login."), self._parent.window)
            self.account_login.grab_focus()
            return False

        if self.account_password.get_text().strip() == "":
            errorWindow(_("You must enter a password."), self._parent.window)
            self.account_password.grab_focus()
            return False
        return True

    def apply(self):
        self._username = self.account_login.get_text().strip()
        self._password = self.account_password.get_text().strip()
        self._consumername = self.consumer_name.get_text()
        self._skip_auto_bind = self.skip_auto_bind.get_active()

        if not self._validate_consumername(self._consumername):
            return DONT_CHANGE

        if not self._validate_account():
            return DONT_CHANGE

        return OWNER_SELECT_PAGE

    def post(self):
        self._parent.username = self._username
        self._parent.password = self._password
        self._parent.consumername = self._consumername
        self._parent.skip_auto_bind = self._skip_auto_bind

        self._backend.create_admin_uep(username=self._username,
                                      password=self._password)

    def clear(self):
        self.account_login.set_text("")
        self.account_password.set_text("")
        self.consumer_name.set_text("")
        self._initialize_consumer_name()
        self.skip_auto_bind.set_active(False)


class ChooseServerScreen(Screen):
    # STYLE ME
    widget_names = Screen.widget_names + [
                'server_entry',
                'proxy_frame',
                'default_button',
                'choose_server_label',
        ]

    def __init__(self, parent, backend):

        super(ChooseServerScreen, self).__init__("choose_server.glade",
                                                 parent, backend)

        self.button_label = _("Next")

        callbacks = {
                "on_default_button_clicked": self._on_default_button_clicked,
                "on_proxy_button_clicked": self._on_proxy_button_clicked,
            }
        self.glade.signal_autoconnect(callbacks)

        self.network_config_dialog = networkConfig.NetworkConfigDialog()

    def _on_default_button_clicked(self, widget):
        # Default port and prefix are fine, so we can be concise and just
        # put the hostname for RHN:
        self.server_entry.set_text(config.DEFAULT_HOSTNAME)

    def _on_proxy_button_clicked(self, widget):
        self.network_config_dialog.set_parent_window(self._parent.window)
        self.network_config_dialog.show()

    def apply(self):
        server = self.server_entry.get_text()
        try:
            (hostname, port, prefix) = parse_server_info(server)
            CFG.set('server', 'hostname', hostname)
            CFG.set('server', 'port', port)
            CFG.set('server', 'prefix', prefix)

            try:
                if not is_valid_server_info(hostname, port, prefix):
                    errorWindow(_("Unable to reach the server at %s:%s%s" %
                        (hostname, port, prefix)), self._parent.window)
                    return DONT_CHANGE
            except MissingCaCertException:
                errorWindow(_("CA certificate for subscription service has not been installed."),
                            self._parent.window)
                return DONT_CHANGE

        except ServerUrlParseError:
            errorWindow(_("Please provide a hostname with optional port and/or prefix: hostname[:port][/prefix]"),
                        self._parent.window)
            return DONT_CHANGE

        log.info("Writing server data to rhsm.conf")
        CFG.save()
        self._backend.update()

        return CREDENTIALS_PAGE

    def clear(self):
        # Load the current server values from rhsm.conf:
        current_hostname = CFG.get('server', 'hostname')
        current_port = CFG.get('server', 'port')
        current_prefix = CFG.get('server', 'prefix')

        # No need to show port and prefix for hosted:
        if current_hostname == config.DEFAULT_HOSTNAME:
            self.server_entry.set_text(config.DEFAULT_HOSTNAME)
        else:
            self.server_entry.set_text("%s:%s%s" % (current_hostname,
                    current_port, current_prefix))


class AsyncBackend(object):

    def __init__(self, backend):
        self.backend = backend
        self.queue = Queue.Queue()

    def _get_owner_list(self, username, callback):
        """
        method run in the worker thread.
        """
        try:
            retval = self.backend.admin_uep.getOwnerList(username)
            self.queue.put((callback, retval, None))
        except Exception, e:
            self.queue.put((callback, None, e))

    def _get_environment_list(self, owner_key, callback):
        """
        method run in the worker thread.
        """
        try:
            retval = None
            # If environments aren't supported, don't bother trying to list:
            if self.backend.admin_uep.supports_resource('environments'):
                log.info("Server supports environments, checking for "
                         "environment to register to.")
                retval = []
                for env in self.backend.admin_uep.getEnvironmentList(owner_key):
                    # We need to ignore the "locker" environment, you can't
                    # register to it:
                    if env['name'].lower() != LIBRARY_ENV_NAME.lower():
                        retval.append(env)
                if len(retval) == 0:
                    raise Exception(_("Server supports environments, but "
                        "none are available."))

            self.queue.put((callback, retval, None))
        except Exception, e:
            log.error("Error listing environments:")
            log.exception(e)
            self.queue.put((callback, None, e))

    def _register_consumer(self, name, facts, owner, env, callback):
        """
        method run in the worker thread.
        """
        try:
            installed_mgr = InstalledProductsManager()
            retval = self.backend.admin_uep.registerConsumer(name=name,
                    facts=facts.get_facts(), owner=owner, environment=env,
                    installed_products=installed_mgr.format_for_server())

            # Facts and installed products went out with the registration
            # request, manually write caches to disk:
            facts.write_cache()
            installed_mgr.write_cache()

            ProfileManager().update_check(self.backend.admin_uep,
                                          retval['uuid'])
            self.queue.put((callback, retval, None))
        except Exception, e:
            self.queue.put((callback, None, e))

    def _subscribe(self, uuid, current_sla, dry_run_result, callback):
        """
        Subscribe to the selected pools.
        """
        try:
            if not current_sla:
                log.info("Saving selected service level for this system.")
                self.backend.uep.updateConsumer(uuid,
                        service_level=dry_run_result.service_level)

            log.info("Binding to subscriptions at service level: %s" %
                    dry_run_result.service_level)
            for pool_quantity in dry_run_result.json:
                pool_id = pool_quantity['pool']['id']
                quantity = pool_quantity['quantity']
                log.info("  pool %s quantity %s" % (pool_id, quantity))
                self.backend.uep.bindByEntitlementPool(uuid, pool_id, quantity)
            managerlib.fetch_certificates(self.backend)
        except Exception, e:
            # Going to try to update certificates just in case we errored out
            # mid-way through a bunch of binds:
            try:
                managerlib.fetch_certificates(self.backend)
            except Exception, cert_update_ex:
                log.info("Error updating certificates after error:")
                log.exception(cert_update_ex)
            self.queue.put((callback, None, e))
            return
        self.queue.put((callback, None, None))

    def _find_suitable_service_levels(self, consumer, facts):
        consumer_json = self.backend.uep.getConsumer(
                consumer.getConsumerId())

        if 'serviceLevel' not in consumer_json:
            raise ServiceLevelNotSupportedException()

        owner_key = consumer_json['owner']['key']

        # This is often "", set to None in that case:
        current_sla = consumer_json['serviceLevel'] or None

        # Using the current date time, we may need to expand this to work
        # with arbitrary dates for future entitling someday:
        sorter = CertSorter(self.backend.product_dir,
                self.backend.entitlement_dir,
                facts.get_facts())

        if len(sorter.installed_products) == 0:
            raise NoProductsException()

        if len(sorter.unentitled_products) == 0:
            raise AllProductsCoveredException()

        if current_sla:
            available_slas = [current_sla]
            log.debug("Using system's current service level: %s" %
                    current_sla)
        else:
            available_slas = self.backend.uep.getServiceLevelList(owner_key)
            log.debug("Available service levels: %s" % available_slas)

        # Will map service level (string) to the results of the dry-run
        # autobind results for each SLA that covers all installed products:
        suitable_slas = {}
        for sla in available_slas:
            dry_run_json = self.backend.uep.dryRunBind(consumer.uuid, sla)
            dry_run = DryRunResult(sla, dry_run_json, sorter)

            # If we have a current SLA for this system, we do not need
            # all products to be covered by the SLA to proceed through
            # this wizard:
            if current_sla or dry_run.covers_required_products():
                suitable_slas[sla] = dry_run
        return (current_sla, sorter.unentitled_products.values(), suitable_slas)

    def _find_service_levels(self, consumer, facts, callback):
        """
        method run in the worker thread.
        """
        try:
            suitable_slas = self._find_suitable_service_levels(consumer, facts)
            self.queue.put((callback, suitable_slas, None))
        except Exception, e:
            self.queue.put((callback, None, e))

    def _watch_thread(self):
        """
        glib idle method to watch for thread completion.
        runs the provided callback method in the main thread.
        """
        try:
            (callback, retval, error) = self.queue.get(block=False)
            if error:
                callback(retval, error=error)
            else:
                callback(retval)
            return False
        except Queue.Empty:
            return True

    def get_owner_list(self, username, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._get_owner_list,
                args=(username, callback)).start()

    def get_environment_list(self, owner_key, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._get_environment_list,
                args=(owner_key, callback)).start()

    def register_consumer(self, name, facts, owner, env, callback):
        """
        Run consumer registration asyncronously
        """
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._register_consumer,
                args=(name, facts, owner, env, callback)).start()

    def subscribe(self, uuid, current_sla, dry_run_result, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._subscribe,
                args=(uuid, current_sla, dry_run_result, callback)).start()

    def find_service_levels(self, consumer, facts, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._find_service_levels,
                args=(consumer, facts, callback)).start()
