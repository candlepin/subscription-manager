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
from subscription_manager.utils import parse_server_info, ServerUrlParseError,\
        is_valid_server_info, MissingCaCertException
from subscription_manager.gui import networkConfig
from subscription_manager.gui import widgets
from subscription_manager.gui.importsub import ImportSubDialog

from subscription_manager.gui.utils import handle_gui_exception, errorWindow


import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("rhsm")
gtk.glade.textdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)
CFG = config.initConfig()

# An implied Katello environment which we can't actual register to.
LIBRARY_ENV_NAME = "library"

DONT_CHANGE = -1
PROGRESS_PAGE = 1
CHOOSE_SERVER_PAGE = 4
CREDENTIALS_PAGE = 0
OWNER_SELECT_PAGE = 3
ENVIRONMENT_SELECT_PAGE = 2
FINISH = 5

REGISTER_ERROR = _("<b>Unable to register the system.</b>") + \
    "\n%s\n" + \
    _("Please see /var/log/rhsm/rhsm.log for more information.")


class RegisterScreen(widgets.GladeWidget):
    """
      Registration Widget Screen
    """

    def __init__(self, backend, consumer, facts=None, callbacks=None):
        """
        Callbacks will be executed when registration status changes.
        """

        widget_names = [
                'register_dialog',
                'register_notebook',
                'register_progressbar',
                'register_details_label',
                'cancel_button',
                'register_button',
                'environment_treeview',
        ]
        widgets.GladeWidget.__init__(self, "registration.glade", widget_names)

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

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Environment"), renderer, text=1)
        self.environment_treeview.set_property("headers-visible", False)
        self.environment_treeview.append_column(column)

        self.organization_screen = OrganizationScreen(self.register_dialog,
                                                      self.backend)
        self.register_notebook.append_page(self.organization_screen.container)

        self.choose_server_screen = ChooseServerScreen(self.register_dialog,
                                                       self.backend)
        self.register_notebook.append_page(self.choose_server_screen.container)

        self.credentials_screen = CredentialsScreen(self.register_dialog,
                                                    self.backend)
        self.register_notebook.prepend_page(self.credentials_screen.container)

    def show(self):
        # Ensure that we start on the first page and that
        # all widgets are cleared.
        self._show_choose_server_page()

        self._clear_registration_widgets()
        self.register_dialog.present()

    def _show_choose_server_page(self):
        # Override the button text to clarify we're not actually registering
        # by pressing that button here.
        self.register_button.set_label(_("Next"))
        self.register_notebook.set_page(CHOOSE_SERVER_PAGE)

    def _show_credentials_page(self):
        # Set the button text back after we changed it when showing the
        # choose server screen.
        self.register_button.set_label(_("Register"))
        self.register_notebook.set_page(CREDENTIALS_PAGE)

    def _delete_event(self, event, data=None):
        return self.close_window()

    def cancel(self, button):
        self.close_window()

    # callback needs the extra arg, so just a wrapper here
    def _on_register_button_clicked(self, button):
        self.register()

    def register(self):
        if self.register_notebook.get_current_page() == CHOOSE_SERVER_PAGE:
            result = self.choose_server_screen.apply()
            if result == FINISH:
                self.close_window()
            elif result == DONT_CHANGE:
                return False
            elif result == CREDENTIALS_PAGE:
                self._show_credentials_page()
                return True
        elif self.register_notebook.get_current_page() == OWNER_SELECT_PAGE:
            self.organization_screen.apply()
            self.owner_key = self.organization_screen.owner_key
            self._owner_selected()
            return True
        elif self.register_notebook.get_current_page() == ENVIRONMENT_SELECT_PAGE:
            self._environment_selected()
            return True
        elif self.register_notebook.get_current_page() == CREDENTIALS_PAGE:
            result = self.credentials_screen.apply()
            if result == DONT_CHANGE:
                return False
            elif result == OWNER_SELECT_PAGE:
                username = self.credentials_screen.username
                password = self.credentials_screen.password
                self.consumername = self.credentials_screen.consumername

                self.backend.create_admin_uep(username=username,
                                              password=password)

                self.async.get_owner_list(username, self._on_get_owner_list_cb)

                self.timer = gobject.timeout_add(100, self._timeout_callback)
                self.register_notebook.set_page(PROGRESS_PAGE)
                self._set_register_details_label(_("Fetching list of possible organizations"))

                self.cancel_button.set_sensitive(False)
                self.register_button.set_sensitive(False)
                return True

    def _timeout_callback(self):
        self.register_progressbar.pulse()
        # return true to keep it pulsing
        return True

    def _on_get_owner_list_cb(self, owners, error=None):
        if error != None:
            handle_gui_exception(error, REGISTER_ERROR,
                    self.register_dialog)
            self._finish_registration(failed=True)
            return

        owners = [(owner['key'], owner['displayName']) for owner in owners]

        if len(owners) == 0:
            handle_gui_exception(None,
                    _("<b>User %s is not able to register with any orgs.</b>") \
                            % (self.account_login.get_text().strip()),
                    self.register_dialog)
            self._finish_registration(failed=True)
            return

        if len(owners) == 1:
            self.owner_key = owners[0][0]
            self._owner_selected()
        else:
            self.organization_screen.set_model(owners)

            self.cancel_button.set_sensitive(True)
            self.register_button.set_sensitive(True)
            self.register_notebook.set_page(OWNER_SELECT_PAGE)

    def _on_get_environment_list_cb(self, result_tuple, error=None):
        environments = result_tuple
        if error != None:
            handle_gui_exception(error, REGISTER_ERROR, self.register_dialog)
            self._finish_registration(failed=True)
            return

        if not environments:
            self._run_register_step(None)
            return

        envs = [(env['id'], env['name']) for env in environments]
        if len(envs) == 1:
            self._run_register_step(envs[0][0])
        else:
            environment_model = gtk.ListStore(str, str)
            for env in envs:
                environment_model.append(env)

            self.environment_treeview.set_model(environment_model)

            self.environment_treeview.get_selection().select_iter(
                    environment_model.get_iter_first())

            self.cancel_button.set_sensitive(True)
            self.register_button.set_sensitive(True)
            self.register_notebook.set_page(ENVIRONMENT_SELECT_PAGE)

    # Callback used by the owner selection screen:
    def _owner_selected(self):
        self.cancel_button.set_sensitive(False)
        self.register_button.set_sensitive(False)
        self.register_notebook.set_page(PROGRESS_PAGE)

        self.async.get_environment_list(self.owner_key,
                                        self._on_get_environment_list_cb)

    def _environment_selected(self):
        self.cancel_button.set_sensitive(False)
        self.register_button.set_sensitive(False)
        self.register_notebook.set_page(PROGRESS_PAGE)

        model, tree_iter = self.environment_treeview.get_selection().get_selected()
        env = model.get_value(tree_iter, 0)

        self._run_register_step(env)

    def _run_register_step(self, env):
        log.info("Registering to owner: %s environment: %s" % (self.owner_key,
                                                               env))
        self.async.register_consumer(self.consumername, self.facts,
                                     self.owner_key, env,
                                     self._on_registration_finished_cb)

        self._set_register_details_label(_("Registering your system"))

    def _on_registration_finished_cb(self, new_account, error=None):
        try:
            if error != None:
                raise error

            managerlib.persist_consumer_cert(new_account)
            self.consumer.reload()
            self._finish_registration()

        except Exception, e:
            handle_gui_exception(e, REGISTER_ERROR, self.register_dialog)
            self._finish_registration(failed=True)

    def _finish_registration(self, failed=False):
        # failed is used by the firstboot subclasses to decide if they should
        # advance the screen or not.
        # XXX it would be cool here to do some async spinning while the
        # main window gui refreshes itself

        if not failed:
            self.close_window()

        self.emit_consumer_signal()

        gobject.source_remove(self.timer)
        self.cancel_button.set_sensitive(True)
        self.register_button.set_sensitive(True)
        self.register_notebook.set_page(CREDENTIALS_PAGE)

    def emit_consumer_signal(self):
        for method in self.callbacks:
            method(skip_auto_bind=self.skip_auto_subscribe())

    def close_window(self):
        self.register_dialog.hide()
        return True

    def skip_auto_subscribe(self):
        return self.credentials_screen.skip_auto_bind.get_active()

    def set_parent_window(self, window):
        self.register_dialog.set_transient_for(window)

    def _set_register_details_label(self, details):
        self.register_details_label.set_label("<small>%s</small>" % details)

    def _clear_registration_widgets(self):
        self.credentials_screen.clear()
        self.choose_server_screen.clear()


class OrganizationScreen(widgets.GladeWidget):

    def __init__(self, parent, backend):
        widget_names = [
                'owner_treeview',
                'container',
        ]
        super(OrganizationScreen, self).__init__("organization.glade",
                                                 widget_names)

        self._parent = parent
        self._backend = backend

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Organization"), renderer, text=1)
        self.owner_treeview.set_property("headers-visible", False)
        self.owner_treeview.append_column(column)

    def apply(self):
        model, tree_iter = self.owner_treeview.get_selection().get_selected()
        self.owner_key = model.get_value(tree_iter, 0)

    def clear(self):
        pass

    def set_model(self, owners):
        owner_model = gtk.ListStore(str, str)
        for owner in owners:
            owner_model.append(owner)

        self.owner_treeview.set_model(owner_model)

        self.owner_treeview.get_selection().select_iter(
                owner_model.get_iter_first())


class CredentialsScreen(widgets.GladeWidget):

    def __init__(self, parent, backend):
        widget_names = [
                'skip_auto_bind',
                'consumer_name',
                'account_login',
                'account_password',
                'container',
        ]
        super(CredentialsScreen, self).__init__("credentials.glade",
                                                 widget_names)

        self._parent = parent
        self._backend = backend

        self._initialize_consumer_name()

        register_tip_label = self.glade.get_widget("registrationTip")
        register_tip_label.set_label("<small>%s</small>" % \
                get_branding().GUI_FORGOT_LOGIN_TIP)

        register_header_label = \
                self.glade.get_widget("registrationHeader")
        register_header_label.set_label("<b>%s</b>" % \
                get_branding().GUI_REGISTRATION_HEADER)

    def _initialize_consumer_name(self):
        if not self.consumer_name.get_text():
            self.consumer_name.set_text(socket.gethostname())

    def _validate_consumername(self, consumername):
        if not consumername:
            errorWindow(_("You must enter a system name."), self._parent)
            self.consumer_name.grab_focus()
            return False
        return True

    def _validate_account(self):
        # validate / check user name
        if self.account_login.get_text().strip() == "":
            errorWindow(_("You must enter a login."), self._parent)
            self.account_login.grab_focus()
            return False

        if self.account_password.get_text().strip() == "":
            errorWindow(_("You must enter a password."), self._parent)
            self.account_password.grab_focus()
            return False
        return True

    def apply(self):
        self.username = self.account_login.get_text().strip()
        self.password = self.account_password.get_text().strip()
        self.consumername = self.consumer_name.get_text()

        if not self._validate_consumername(self.consumername):
            return DONT_CHANGE

        if not self._validate_account():
            return DONT_CHANGE

        return OWNER_SELECT_PAGE

    def clear(self):
        self.account_login.set_text("")
        self.account_password.set_text("")
        self.consumer_name.set_text("")
        self._initialize_consumer_name()
        self.skip_auto_bind.set_active(False)


class ChooseServerScreen(widgets.GladeWidget):

    def __init__(self, parent, backend):
        widget_names = [
                'rhn_radio',
                'local_radio',
                'offline_radio',
                'local_entry',
                'import_certs_button',
                'proxy_label',
                'proxy_config_button',
                'container',
        ]
        super(ChooseServerScreen, self).__init__("choose_server.glade",
                                                 widget_names)

        self._parent = parent
        self._backend = backend

        callbacks = {
                "on_proxy_config_button_clicked": self._on_proxy_config_button_clicked,
                "on_import_certs_button_clicked": self._on_import_certs_button_clicked,
                "on_rhn_radio_toggled": self._on_server_radio_toggled,
                "on_local_radio_toggled": self._on_server_radio_toggled,
                "on_offline_radio_toggled": self._on_server_radio_toggled,
            }
        self.glade.signal_autoconnect(callbacks)

        self.network_config_dialog = networkConfig.NetworkConfigDialog()
        self.import_certs_dialog = ImportSubDialog()

    def _on_server_radio_toggled(self, widget):
        self.local_entry.set_sensitive(self.local_radio.get_active())

    def _on_proxy_config_button_clicked(self, button):
        self.network_config_dialog.set_parent_window(self._parent)
        self.network_config_dialog.show()

    def _on_import_certs_button_clicked(self, button):
        self.import_certs_dialog.set_parent_window(self._parent)
        self.import_certs_dialog.show()

    def apply(self):
        if self.rhn_radio.get_active():
            CFG.set('server', 'hostname', config.DEFAULT_HOSTNAME)
            CFG.set('server', 'port', config.DEFAULT_PORT)
            CFG.set('server', 'prefix', config.DEFAULT_PREFIX)
        elif self.offline_radio.get_active():
            # We'll signal the user set offline by setting an empty hostname:
            CFG.set('server', 'hostname', '')
            CFG.set('server', 'port', config.DEFAULT_PORT)
            CFG.set('server', 'prefix', config.DEFAULT_PREFIX)
        elif self.local_radio.get_active():
            local_server = self.local_entry.get_text()
            try:
                (hostname, port, prefix) = parse_server_info(local_server)
                CFG.set('server', 'hostname', hostname)
                CFG.set('server', 'port', port)
                CFG.set('server', 'prefix', prefix)

                try:
                    if not is_valid_server_info(hostname, port, prefix):
                        errorWindow(_("Unable to reach the server at %s:%s%s" %
                            (hostname, port, prefix)), self._parent)
                        return DONT_CHANGE
                except MissingCaCertException:
                    errorWindow(_("CA certificate for subscription service has not been installed."), self._parent)
                    return DONT_CHANGE

            except ServerUrlParseError:
                errorWindow(_("Please provide a hostname with optional port and/or prefix: hostname[:port][/prefix]"), self._parent)
                return DONT_CHANGE

        log.info("Writing server data to rhsm.conf")
        CFG.save()
        self._backend.update()

        if self.offline_radio.get_active():
            # Because the user selected offline, the whole registration process
            # must end here.
            return FINISH
        else:
            return CREDENTIALS_PAGE

    def clear(self):
        self.local_entry.set_text("")

        # We need to determine the current state of the server info in
        # the config file so we can pre-select the correct options:
        current_hostname = CFG.get('server', 'hostname')
        current_port = CFG.get('server', 'port')
        current_prefix = CFG.get('server', 'prefix')
        if current_hostname == config.DEFAULT_HOSTNAME:
            self.rhn_radio.set_active(True)
        elif current_hostname == "":
            self.offline_radio.set_active(True)
        else:
            self.local_radio.set_active(True)
            self.local_entry.set_text("%s:%s%s" % (current_hostname,
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
                log.info("Server supports environments, checking for environment to "
                        "register to.")
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

            # Facts and installed products went out with the registration request,
            # manually write caches to disk:
            facts.write_cache()
            installed_mgr.write_cache()

            ProfileManager().update_check(self.backend.admin_uep, retval['uuid'])
            self.queue.put((callback, retval, None))
        except Exception, e:
            self.queue.put((callback, None, e))

    def _bind_by_products(self, uuid, callback):
        """
        method run in the worker thread.
        """
        try:
            retval = self.backend.uep.bind(uuid)
            self.queue.put((callback, retval, None))
        except Exception, e:
            self.queue.put((callback, None, e))

    def _fetch_certificates(self, callback):
        """
        method run in the worker thread.
        """
        try:
            managerlib.fetch_certificates(self.backend)
            self.queue.put((callback, None, None))
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

    def bind_by_products(self, uuid, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._bind_by_products,
                args=(uuid, callback)).start()

    def fetch_certificates(self, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._fetch_certificates,
                args=(callback,)).start()
