
#
# Copyright (c) 2010 Red Hat, Inc.
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

import gettext
import logging
import os
import threading
#from gi.repository import GObject
import socket

import rhsm.config
import rhsm.connection as connection
import rhsm.utils
from rhsm.utils import remove_scheme
from rhsm.utils import parse_url

from subscription_manager import ga
from subscription_manager.gui.utils import show_error_window
import subscription_manager.injection as inj

from subscription_manager.gui import progress
from subscription_manager.gui import widgets

_ = gettext.gettext

DIR = os.path.dirname(__file__)

log = logging.getLogger('rhsm-app.' + __name__)


class NetworkConfigDialog(widgets.SubmanBaseWidget):
    """This is the dialog that allows setting http proxy settings.

    It uses the instant apply paradigm or whatever you wanna call it that the
    gnome HIG recommends. Whenever a toggle button is flipped or a text entry
    changed, the new setting will be saved.

    """
    widget_names = ["networkConfigDialog", "enableProxyButton", "enableProxyAuthButton",
                    "proxyEntry", "proxyUserEntry", "proxyPasswordEntry",
                    "cancelButton", "saveButton", "testConnectionButton",
                    "connectionStatusLabel"]
    gui_file = "networkConfig.glade"

    def __init__(self):
        # Get widgets we'll need to access

        super(NetworkConfigDialog, self).__init__()
        self.org_timeout = socket.getdefaulttimeout()
        self.progress_bar = None

        self.cfg = rhsm.config.initConfig()
        self.cp_provider = inj.require(inj.CP_PROVIDER)

        # Need to load values before connecting signals because when the dialog
        # starts up it seems to trigger the signals which overwrites the config
        # with the blank values.
        self.set_initial_values()
        self.enableProxyButton.connect("toggled", self.enable_action)
        self.enableProxyAuthButton.connect("toggled", self.enable_action)

        self.enableProxyButton.connect("toggled", self.clear_connection_label)
        self.enableProxyAuthButton.connect("toggled", self.clear_connection_label)

        self.enableProxyButton.connect("toggled", self.enable_test_button)

        self.proxyEntry.connect("changed", self.clear_connection_label)
        self.proxyUserEntry.connect("changed", self.clear_connection_label)
        self.proxyPasswordEntry.connect("changed", self.clear_connection_label)

        self.proxyEntry.connect("focus-out-event", self.clean_proxy_entry)

        self.cancelButton.connect("clicked", self.on_cancel_clicked)
        self.saveButton.connect("clicked", self.on_save_clicked)
        self.testConnectionButton.connect("clicked", self.on_test_connection_clicked)

        self.networkConfigDialog.connect("delete-event", self.deleted)

    def set_initial_values(self):
        proxy_url = self.cfg.get("server", "proxy_hostname") or ""
        # append port unless not specified, then append the default of 3128
        if proxy_url:
            proxy_url = proxy_url + ':' + (self.cfg.get("server", "proxy_port") or rhsm.config.DEFAULT_PROXY_PORT)

        self.proxyEntry.set_text("%s" % proxy_url)

        # show proxy/proxy auth sections as being enabled if we have values set
        # rhn actualy has a seperate for config flag for enabling, which seems overkill
        if self.cfg.get("server", "proxy_hostname"):
            self.enableProxyButton.set_active(True)
        if self.cfg.get("server", "proxy_hostname") and self.cfg.get("server", "proxy_user"):
            self.enableProxyAuthButton.set_active(True)

        self.enable_action(self.enableProxyAuthButton)
        self.enable_action(self.enableProxyButton)

        # the extra or "" are to make sure we don't str None
        self.proxyUserEntry.set_text(str(self.cfg.get("server", "proxy_user") or ""))
        self.proxyPasswordEntry.set_text(str(self.cfg.get("server", "proxy_password") or ""))
        self.connectionStatusLabel.set_label("")
        # If there is no proxy information, disable the proxy test
        # button.
        if not self.enableProxyButton.get_active():
            self.testConnectionButton.set_sensitive(False)
            self.enableProxyAuthButton.set_sensitive(False)

    def write_values(self, widget=None, dummy=None):
        proxy = self.proxyEntry.get_text() or ""

        # don't save these values if they are disabled in the gui
        if proxy and self.enableProxyButton.get_active():
            # Remove any URI scheme provided
            proxy = remove_scheme(proxy)
            # Update the proxy entry field to show we removed any scheme
            self.proxyEntry.set_text(proxy)
            try:
                proxy_hostname, proxy_port = proxy.split(':')
                self.cfg.set("server", "proxy_hostname", proxy_hostname)
                self.cfg.set("server", "proxy_port", proxy_port)
            except ValueError:
                # no port? just write out the hostname and assume default
                self.cfg.set("server", "proxy_hostname", proxy)
                self.cfg.set("server", "proxy_port", rhsm.config.DEFAULT_PROXY_PORT)
        else:
            # delete config options if we disable it in the ui
            self.cfg.set("server", "proxy_hostname", "")
            self.cfg.set("server", "proxy_port", "")

        if self.enableProxyAuthButton.get_active():
            if self.proxyUserEntry.get_text() is not None:
                self.cfg.set("server", "proxy_user",
                             str(self.proxyUserEntry.get_text()))

            if self.proxyPasswordEntry.get_text() is not None:
                self.cfg.set("server", "proxy_password",
                             str(self.proxyPasswordEntry.get_text()))
        else:
            self.cfg.set("server", "proxy_user", "")
            self.cfg.set("server", "proxy_password", "")

        try:
            self.cfg.save()
            self.cp_provider.set_connection_info()
        except Exception:
            show_error_window(_("There was an error saving your configuration.") +
                              _("Make sure that you own %s.") % self.cfg.fileName,
                                parent=self.networkConfigDialog)

    def show(self):
        self.set_initial_values()
        self.networkConfigDialog.present()

    def on_save_clicked(self, button):
        self.write_values()
        self.networkConfigDialog.hide()

    def on_cancel_clicked(self, button):
        self.networkConfigDialog.hide()

    def enable_test_button(self, button):
        self.testConnectionButton.set_sensitive(button.get_active())

    def clear_connection_label(self, entry):
        self.connectionStatusLabel.set_label("")

        # only used as callback from test_connection thread
    def on_test_connection_finish(self, result):
        if result:
            self.connectionStatusLabel.set_label(_("Proxy connection succeeded"))
        else:
            self.connectionStatusLabel.set_label(_("Proxy connection failed"))
        self._clear_progress_bar()

    def _reset_socket_timeout(self):
        socket.setdefaulttimeout(self.org_timeout)

    def test_connection_wrapper(self, proxy_host, proxy_port, proxy_user, proxy_password):
        connection_status = self.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)
        ga.GObject.idle_add(self.on_test_connection_finish, connection_status)

    def test_connection(self, proxy_host, proxy_port, proxy_user, proxy_password):
        cp = connection.UEPConnection(
                    proxy_hostname=proxy_host,
                    proxy_port=proxy_port,
                    proxy_user=proxy_user,
                    proxy_password=proxy_password)
        try:
            socket.setdefaulttimeout(10)
            cp.getStatus()

        # Either connection.RemoteServerException or connection.RestLibExecption are considered
        # acceptable exceptions because they are only thrown as a response from the server. Meaning the
        # connection through the proxy was successful.
        except (connection.RemoteServerException,
                connection.RestlibException) as e:
            log.warn("Reporting proxy connection as good despite %s" %
             e)
            return True
        except connection.NetworkException, e:
            log.warn("%s when attempting to connect through %s:%s" %
             (e.code, proxy_host, proxy_port))
            return False
        except Exception, e:
            log.exception("'%s' when attempting to connect through %s:%s" %
                      (e, proxy_host, proxy_port))
            return False
        else:
            return True
        finally:
            self._reset_socket_timeout()

    # Pass through of the return values of parse_proxy_entry
    # This was done to simplify on_test_connection_clicked
    def clean_proxy_entry(self, widget=None, dummy=None):
        proxy_url = self.proxyEntry.get_text()
        proxy_host, proxy_port = self.parse_proxy_entry(proxy_url)
        cleaned_proxy_url = "%s:%s" % (proxy_host, proxy_port)
        self.proxyEntry.set_text(cleaned_proxy_url)
        return (proxy_host, proxy_port)

    def parse_proxy_entry(self, proxy_url):
        proxy_url = remove_scheme(proxy_url)
        proxy_host = None
        proxy_port = None
        try:
            proxy_info = parse_url(proxy_url, default_port=rhsm.config.DEFAULT_PROXY_PORT)
            proxy_host = proxy_info[2]
            proxy_port = proxy_info[3]

        except rhsm.utils.ServerUrlParseErrorPort, e:
            proxy_host = proxy_url.split(':')[0]
            proxy_port = rhsm.config.DEFAULT_PROXY_PORT
        except rhsm.utils.ServerUrlParseError, e:
            log.error(e)
        return (proxy_host, proxy_port)

    def on_test_connection_clicked(self, button):
        proxy_host, proxy_port = self.clean_proxy_entry()

        # ensure that we only use those values for testing if required
        # this catches the case where there was previously a user and pass in the config
        # and the user unchecks the box, leaving behind the values for the time being.
        # Alternatively we could clear those boxes when the box is unchecked
        if self.enableProxyAuthButton.get_active():
            proxy_user = self.proxyUserEntry.get_text()
            proxy_password = self.proxyPasswordEntry.get_text()
        else:
            proxy_user = None
            proxy_password = None

        self._display_progress_bar()
        threading.Thread(target=self.test_connection_wrapper,
                         args=(proxy_host, proxy_port, proxy_user, proxy_password),
                         name='test_connection_thread').start()

    def deleted(self, event, data):
        self.write_values()
        self.networkConfigDialog.hide()
        self._clear_progress_bar()
        return True

    def _display_progress_bar(self):
        if self.progress_bar:
            self.progress_bar.set_title(_("Testing Connection"))
            self.progress_bar.set_label(_("Please wait"))
        else:
            self.progress_bar = progress.Progress(_("Testing Connection"), _("Please wait"))
            self.timer = ga.GObject.timeout_add(100, self.progress_bar.pulse)
            self.progress_bar.set_parent_window(self.networkConfigDialog)

    def _clear_progress_bar(self):
        if not self.progress_bar:  # progress bar could be none iff self.test_connection is called directly
            return

        self.progress_bar.hide()
        ga.GObject.source_remove(self.timer)
        self.timer = 0
        self.progress_bar = None

    def enable_action(self, button):
        if button.get_name() == "enableProxyButton":
            self.proxyEntry.set_sensitive(button.get_active())
            self.proxyEntry.grab_focus()
            self.enableProxyAuthButton.set_sensitive(button.get_active())
            # Proxy authentication should only be active if proxy is also enabled
            self.proxyUserEntry.set_sensitive(button.get_active() and
                    self.enableProxyAuthButton.get_active())
            self.proxyPasswordEntry.set_sensitive(button.get_active() and
                    self.enableProxyAuthButton.get_active())
        elif button.get_name() == "enableProxyAuthButton":
            self.proxyUserEntry.set_sensitive(button.get_active())
            self.proxyPasswordEntry.set_sensitive(button.get_active())
            self.get_object("usernameLabel").set_sensitive(button.get_active())
            self.get_object("passwordLabel").set_sensitive(button.get_active())

    def set_parent_window(self, window):
        self.networkConfigDialog.set_transient_for(window)
