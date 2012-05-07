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

import os
import socket
import logging

import gtk
import gtk.glade


from subscription_manager import managerlib
import rhsm.config as config
from subscription_manager import constants
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.branding import get_branding
from subscription_manager.cache import ProfileManager, InstalledProductsManager
from subscription_manager.utils import parse_server_info

from subscription_manager.gui.utils import handle_gui_exception, errorWindow, \
    GladeWrapper

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("rhsm")
gtk.glade.textdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)

prefix = os.path.dirname(__file__)
VALID_IMG = os.path.join(prefix, "data/icons/valid.svg")
INVALID_IMG = os.path.join(prefix, "data/icons/invalid.svg")

# An implied Katello environment which we can't actual register to.
LIBRARY_ENV_NAME = "library"

cert_file = ConsumerIdentity.certpath()
key_file = ConsumerIdentity.keypath()

CFG = config.initConfig()

import threading
import Queue

import gobject

CREDENTIALS_PAGE = 0
PROGRESS_PAGE = 1
OWNER_SELECT_PAGE = 2
ENVIRONMENT_SELECT_PAGE = 3
CHOOSE_SERVER_PAGE = 4


registration_xml = GladeWrapper(os.path.join(prefix,
    "data/registration.glade"))


class RegisterScreen:
    """
      Registration Widget Screen
    """

    def __init__(self, backend, consumer, facts=None, callbacks=None):
        """
        Callbacks will be executed when registration status changes.
        """
        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.callbacks = callbacks

        self.async = AsyncBackend(self.backend)

        dic = {"on_register_cancel_button_clicked": self.cancel,
               "on_register_button_clicked": self.on_register_button_clicked,
            }

        registration_xml.signal_autoconnect(dic)
        self.registerWin = registration_xml.get_widget("register_dialog")
        self.registerWin.connect("hide", self.cancel)
        self.registerWin.connect("delete_event", self.delete_event)
        self.initializeConsumerName()

        self.uname = registration_xml.get_widget("account_login")
        self.passwd = registration_xml.get_widget("account_password")
        self.consumer_name = registration_xml.get_widget("consumer_name")
        self.skip_auto_bind = registration_xml.get_widget("skip_auto_bind")

        self.register_notebook = \
                registration_xml.get_widget("register_notebook")
        self.register_progressbar = \
                registration_xml.get_widget("register_progressbar")
        self.register_details_label = \
                registration_xml.get_widget("register_details_label")

        self.owner_treeview = registration_xml.get_widget("owner_treeview")
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Organization"), renderer, text=1)
        self.owner_treeview.set_property("headers-visible", False)
        self.owner_treeview.append_column(column)

        self.environment_treeview = registration_xml.get_widget("environment_treeview")
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Environment"), renderer, text=1)
        self.environment_treeview.set_property("headers-visible", False)
        self.environment_treeview.append_column(column)

        self.cancel_button = registration_xml.get_widget("cancel_button")
        self.register_button = registration_xml.get_widget("register_button")

        register_tip_label = registration_xml.get_widget("registrationTip")
        register_tip_label.set_label("<small>%s</small>" % \
                get_branding().GUI_FORGOT_LOGIN_TIP)

        register_header_label = \
                registration_xml.get_widget("registrationHeader")
        register_header_label.set_label("<b>%s</b>" % \
                get_branding().GUI_REGISTRATION_HEADER)

        self.rhn_radio = registration_xml.get_widget("rhn_radio")
        self.local_radio = registration_xml.get_widget("local_radio")
        self.offline_radio = registration_xml.get_widget("offline_radio")

        self.local_entry = registration_xml.get_widget("local_entry")

    def show(self):
        # Ensure that we start on the first page and that
        # all widgets are cleared.
        self.register_notebook.set_page(CHOOSE_SERVER_PAGE)

        self._clear_registration_widgets()
        self.registerWin.present()

    def delete_event(self, event, data=None):
        return self.close_window()

    def cancel(self, button):
        self.close_window()

    def initializeConsumerName(self):
        consumername = registration_xml.get_widget("consumer_name")
        if not consumername.get_text():
            consumername.set_text(socket.gethostname())

    # callback needs the extra arg, so just a wrapper here
    def on_register_button_clicked(self, button):
        self.register()

    def register(self, testing=None):
        if self.register_notebook.get_current_page() == CHOOSE_SERVER_PAGE:
            self._server_selected()
            return True
        if self.register_notebook.get_current_page() == OWNER_SELECT_PAGE:
            # we're on the owner select page
            self._owner_selected()
            return True
        elif self.register_notebook.get_current_page() == ENVIRONMENT_SELECT_PAGE:
            self._environment_selected()
            return True

        username = self.uname.get_text().strip()
        password = self.passwd.get_text().strip()
        consumername = self.consumer_name.get_text()

        if not self.validate_consumername(consumername):
            return False

        if not self.validate_account():
            return False

        # for firstboot -t
        if testing:
            return True

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
            handle_gui_exception(error, constants.REGISTER_ERROR,
                    self.registerWin)
            self._finish_registration(failed=True)
            return

        owners = [(owner['key'], owner['displayName']) for owner in owners]

        if len(owners) == 0:
            handle_gui_exception(None,
                    (constants.NO_ORG_ERROR % (self.uname.get_text().strip())),
                    self.registerWin)
            self._finish_registration(failed=True)
            return

        if len(owners) == 1:
            self.owner_key = owners[0][0]
            self.async.get_environment_list(self.owner_key, self._on_get_environment_list_cb)

        else:
            owner_model = gtk.ListStore(str, str)
            for owner in owners:
                owner_model.append(owner)

            self.owner_treeview.set_model(owner_model)

            self.owner_treeview.get_selection().select_iter(
                    owner_model.get_iter_first())

            self.cancel_button.set_sensitive(True)
            self.register_button.set_sensitive(True)
            self.register_notebook.set_page(OWNER_SELECT_PAGE)

    def _on_get_environment_list_cb(self, result_tuple, error=None):
        environments = result_tuple
        if error != None:
            handle_gui_exception(error, constants.REGISTER_ERROR, self.registerWin)
            self._finish_registration(failed=True)
            return

        if not environments:
            self._run_register_step(self.owner_key, None)
            return

        envs = [(env['id'], env['name']) for env in environments]
        if len(envs) == 1:
            self._run_register_step(self.owner_key, envs[0][0])
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

        model, tree_iter = self.owner_treeview.get_selection().get_selected()
        self.owner_key = model.get_value(tree_iter, 0)

        self.async.get_environment_list(self.owner_key, self._on_get_environment_list_cb)

    def _server_selected(self):
        self.register_notebook.set_page(CREDENTIALS_PAGE)
        if self.rhn_radio.get_active():
            CFG.set('server', 'hostname', constants.DEFAULT_HOSTNAME)
            CFG.set('server', 'port', constants.DEFAULT_PORT)
            CFG.set('server', 'prefix', constants.DEFAULT_PREFIX)
        elif self.offline_radio.get_active():
            # We'll signal the user set offline by setting an empty hostname:
            CFG.set('server', 'hostname', '')
            CFG.set('server', 'port', constants.DEFAULT_PORT)
            CFG.set('server', 'prefix', constants.DEFAULT_PREFIX)
        elif self.local_radio.get_active():
            local_server = self.local_entry.get_text()
            (hostname, port, prefix) = parse_server_info(local_server)

            CFG.set('server', 'hostname', hostname)
            CFG.set('server', 'port', port)
            CFG.set('server', 'prefix', prefix)

        log.info("Writing server data to rhsm.conf")
        CFG.save()


    def _environment_selected(self):
        self.cancel_button.set_sensitive(False)
        self.register_button.set_sensitive(False)
        self.register_notebook.set_page(PROGRESS_PAGE)

        model, tree_iter = self.environment_treeview.get_selection().get_selected()
        env = model.get_value(tree_iter, 0)

        self._run_register_step(self.owner_key, env)

    def _run_register_step(self, owner, env):
        log.info("Registering to owner: %s environment: %s" % (owner, env))
        self.async.register_consumer(self.consumer_name.get_text(),
                self.facts, owner, env,
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
            handle_gui_exception(e, constants.REGISTER_ERROR, self.registerWin)
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
        self.registerWin.hide()
        return True

    def skip_auto_subscribe(self):
        return self.skip_auto_bind.get_active()

    def validate_consumername(self, consumername):
        if not consumername:
            errorWindow(_("You must enter a system name."), parent=self.registerWin)
            self.consumer_name.grab_focus()
            return False
        return True

    def validate_account(self):
        # validate / check user name
        if self.uname.get_text().strip() == "":
            errorWindow(_("You must enter a login."), parent=self.registerWin)
            self.uname.grab_focus()
            return False

        if self.passwd.get_text().strip() == "":
            errorWindow(_("You must enter a password."), parent=self.registerWin)
            self.passwd.grab_focus()
            return False
        return True

    def set_parent_window(self, window):
        self.registerWin.set_transient_for(window)

    def _set_register_details_label(self, details):
        self.register_details_label.set_label("<small>%s</small>" % details)

    def _clear_registration_widgets(self):
        self.uname.set_text("")
        self.passwd.set_text("")
        self.consumer_name.set_text("")
        self.initializeConsumerName()
        self.skip_auto_bind.set_active(False)
        self.local_entry.set_text("")

        # We need to determine the current state of the server info in
        # the config file so we can pre-select the correct options:
        current_hostname = CFG.get('server', 'hostname')
        current_port = CFG.get('server', 'port')
        current_prefix = CFG.get('server', 'prefix')
        if current_hostname == constants.DEFAULT_HOSTNAME:
            print("RHN server pre-selected.")
            self.rhn_radio.set_active(True)
        elif current_hostname == "":
            print("Offline pre-selected.")
            self.offline_radio.set_active(True)
        else:
            print("Local server pre-selected.")
            self.local_radio.set_active(True)
            self.local_entry.set_text("%s:%s%s" % (current_hostname,
                current_port, current_prefix))


    def _show_credentials_page(self):
        self.register_notebook.set_page(CREDENTIALS_PAGE)


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
