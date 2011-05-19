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

from subscription_manager.gui import messageWindow
from subscription_manager.gui import networkConfig
from subscription_manager import managerlib
from subscription_manager.gui import file_monitor
import rhsm.connection as connection
import rhsm.config as config
from subscription_manager import constants
from subscription_manager.facts import Facts
from subscription_manager.certlib import ProductDirectory, EntitlementDirectory, ConsumerIdentity, \
        CertLib, CertSorter, find_first_invalid_date
from subscription_manager.branding import get_branding

from subscription_manager.gui import activate
from subscription_manager.gui import factsgui
from subscription_manager.gui import widgets
from subscription_manager.gui.installedtab import InstalledProductsTab
from subscription_manager.gui.mysubstab import MySubscriptionsTab
from subscription_manager.gui.allsubs import AllSubscriptionsTab
from subscription_manager.gui.subscription_assistant import \
        SubscriptionAssistant
from subscription_manager.gui.importsub import ImportSubDialog
from subscription_manager.gui.utils import handle_gui_exception, errorWindow, linkify
from datetime import datetime

import gettext
_ = gettext.gettext
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)

prefix = os.path.dirname(__file__)
VALID_IMG = os.path.join(prefix, "data/icons/valid.svg")
INVALID_IMG = os.path.join(prefix, "data/icons/invalid.svg")

cert_file = ConsumerIdentity.certpath()
key_file = ConsumerIdentity.keypath()

cfg = config.initConfig()

import threading
import Queue

import gobject


class GladeWrapper(gtk.glade.XML):
    def __init__(self, filename):
        gtk.glade.XML.__init__(self, filename)

    def get_widget(self, widget_name):
        widget = gtk.glade.XML.get_widget(self, widget_name)
        if widget is None:
            print "ERROR: widget %s was not found" % widget_name
            raise Exception ("Widget %s not found" % widget_name)
        return widget

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
               "on_register_button_clicked": self.onRegisterAction,
            }

        registration_xml.signal_autoconnect(dic)
        self.registerWin = registration_xml.get_widget("register_dialog")
        self.registerWin.connect("hide", self.cancel)
        self.registerWin.connect("delete_event", self.delete_event)
        self.initializeConsumerName()

        self.uname = registration_xml.get_widget("account_login")
        self.passwd = registration_xml.get_widget("account_password")
        self.consumer_name = registration_xml.get_widget("consumer_name")
        
        self.register_notebook = \
                registration_xml.get_widget("register_notebook")
        self.register_progressbar = \
                registration_xml.get_widget("register_progressbar")
        self.register_details_label = \
                registration_xml.get_widget("register_details_label")

        self.cancel_button = registration_xml.get_widget("cancel_button")
        self.register_button = registration_xml.get_widget("register_button")

        register_tip_label = registration_xml.get_widget("registrationTip")
        register_tip_label.set_label("<small>%s</small>" % \
                linkify(get_branding().GUI_FORGOT_LOGIN_TIP))

        register_header_label = \
                registration_xml.get_widget("registrationHeader")
        register_header_label.set_label("<b>%s</b>" % \
                get_branding().GUI_REGISTRATION_HEADER)

    def show(self):
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
    def onRegisterAction(self, button):
        self.register()

    def register(self, testing=None):
        username = self.uname.get_text()
        password = self.passwd.get_text()
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
        self.async.register_consumer(consumername, self.facts.get_facts(),
                self.on_registration_finished_cb)

        self.timer = gobject.timeout_add(100, self._timeout_callback)
        self.register_notebook.set_page(1)
        self._set_register_details_label(_("Registering your system"))

        self.cancel_button.set_sensitive(False)
        self.register_button.set_sensitive(False)

    def _timeout_callback(self):
        self.register_progressbar.pulse()
        # return true to keep it pulsing
        return True

    def on_registration_finished_cb(self, new_account, error=None):

        try:
            if error != None:
                raise error

            managerlib.persist_consumer_cert(new_account)
            self.consumer.reload()
            # reload CP instance with new ssl certs
            if self.auto_subscribe():
                self._set_register_details_label(_("Autosubscribing"))
                # try to auomatically bind products
                products = managerlib.getInstalledProductHashMap()
                self.async.bind_by_products(self.consumer.uuid, products,
                        self._on_bind_by_products_cb)
            else:
                self._finish_registration()

        except Exception, e:
           handle_gui_exception(e, constants.REGISTER_ERROR)
           self._finish_registration()

    def _on_bind_by_products_cb(self, products, error=None):
        if error:
            log.exception(error)
            log.warning("Warning: Unable to auto subscribe to %s" \
                    % ", ".join(products.keys()))
        else:
            log.info("Automatically subscribed to products: %s " \
                    % ", ".join(products.keys()))

        self._set_register_details_label("Fetching certificates")
        self.async.fetch_certificates(self._on_fetch_certificates_cb)

    def _on_fetch_certificates_cb(self, error=None):
        if error:
            handle_gui_exception(error)
        self._finish_registration()

    def _finish_registration(self):
        self.close_window()
        self.emit_consumer_signal()

        gobject.source_remove(self.timer)
        self.cancel_button.set_sensitive(True)
        self.register_button.set_sensitive(True)
        self.register_notebook.set_page(0)

    def emit_consumer_signal(self):
        for method in self.callbacks:
            method()

    def close_window(self):
        self.registerWin.hide()
        return True

    def auto_subscribe(self):
        self.autobind = registration_xml.get_widget("auto_bind")
        return self.autobind.get_active()

    def validate_consumername(self, consumername):
        if not consumername:
            errorWindow(_("You must enter a system name."))
            self.consumer_name.grab_focus()
            return False
        return True

    def validate_account(self):
        # validate / check user name
        if self.uname.get_text().strip() == "":
            errorWindow(_("You must enter a login."))
            self.uname.grab_focus()
            return False

        if self.passwd.get_text().strip() == "":
            errorWindow(_("You must enter a password."))
            self.passwd.grab_focus()
            return False
        return True

    def set_parent_window(self, window):
        self.registerWin.set_transient_for(window)

    def _set_register_details_label(self, details):
        self.register_details_label.set_label("<small>%s</small>" % details)


class AsyncBackend(object):

    def __init__(self, backend):
        self.backend = backend
        self.queue = Queue.Queue()

    def _register_consumer(self, name, facts, callback):
        """
        method run in the worker thread.
        """
        try:
            retval = self.backend.admin_uep.registerConsumer(name=name,
                    facts=facts)
            self.queue.put((callback, retval, None))
        except Exception, e:
            self.queue.put((callback, None, e))

    def _bind_by_products(self, uuid, products, callback):
        """
        method run in the worker thread.
        """
        try:
            self.backend.uep.bindByProduct(uuid, products.values())
            self.queue.put((callback, products, None))
        except Exception, e:
            self.queue.put((callback, products, e))

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
        except Queue.Empty, e:
            return True

    def register_consumer(self, name, facts, callback):
        """
        Run consumer registration asyncronously
        """
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._register_consumer,
                args=(name, facts, callback)).start()

    def bind_by_products(self, uuid, products, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._bind_by_products,
                args=(uuid, products, callback)).start()

    def fetch_certificates(self, callback):
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._fetch_certificates,
                args=(callback,)).start()
