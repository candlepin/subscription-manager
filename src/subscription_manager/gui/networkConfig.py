
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

import os
import gettext
import gtk
import gtk.glade
import logging

import rhsm.config
import rhsm.connection as connection

from subscription_manager.gui.utils import errorWindow
from subscription_manager.utils import remove_scheme

_ = gettext.gettext

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/networkConfig.glade")

log = logging.getLogger('rhsm-app.' + __name__)


class NetworkConfigDialog:
    """This is the dialog that allows setting http proxy settings.

    It uses the instant apply paradigm or whatever you wanna call it that the
    gnome HIG recommends. Whenever a toggle button is flipped or a text entry
    changed, the new setting will be saved.

    """

    def __init__(self):
        self.xml = gtk.glade.XML(GLADE_XML)
        # Get widgets we'll need to access
        self.dlg = self.xml.get_widget("networkConfigDialog")
        self.enableProxyButton = self.xml.get_widget("enableProxyButton")
        self.enableProxyAuthButton = self.xml.get_widget("enableProxyAuthButton")
        self.proxyEntry = self.xml.get_widget("proxyEntry")
        self.proxyUserEntry = self.xml.get_widget("proxyUserEntry")
        self.proxyPasswordEntry = self.xml.get_widget("proxyPasswordEntry")

        self.cfg = rhsm.config.initConfig()

        # Need to load values before connecting signals because when the dialog
        # starts up it seems to trigger the signals which overwrites the config
        # with the blank values.
        self.setInitialValues()
        self.enableProxyButton.connect("toggled", self.enableAction)
        self.enableProxyAuthButton.connect("toggled", self.enableAction)

        self.enableProxyButton.connect("toggled", self.writeValues)
        self.enableProxyAuthButton.connect("toggled", self.writeValues)

        self.enableProxyButton.connect("toggled", self.clearConnectionLabel)
        self.enableProxyAuthButton.connect("toggled", self.clearConnectionLabel)

        self.enableProxyButton.connect("toggled", self.enableTestButton)

        self.proxyEntry.connect("focus-out-event", self.writeValues)
        self.proxyUserEntry.connect("focus-out-event", self.writeValues)
        self.proxyPasswordEntry.connect("focus-out-event", self.writeValues)

        self.proxyEntry.connect("changed", self.clearConnectionLabel)
        self.proxyUserEntry.connect("changed", self.clearConnectionLabel)
        self.proxyPasswordEntry.connect("changed", self.clearConnectionLabel)

        self.xml.get_widget("closeButton").connect("clicked", self.close)
        self.xml.get_widget("testConnectionButton").connect("clicked", \
                self.displayConnectionStatus)
        self.dlg.connect("delete-event", self.deleted)

    def setInitialValues(self):
        proxy_url = self.cfg.get("server", "proxy_hostname") or ""
        # append port unless not specified, then append the default of 3128
        if proxy_url:
            proxy_url = proxy_url + ':' + (self.cfg.get("server", "proxy_port") or rhsm.config.DEFAULT_PROXY_PORT)

        self.xml.get_widget("proxyEntry").set_text("%s" % proxy_url)

        # show proxy/proxy auth sections as being enabled if we have values set
        # rhn actualy has a seperate for config flag for enabling, which seems overkill
        if self.cfg.get("server", "proxy_hostname"):
            self.xml.get_widget("enableProxyButton").set_active(True)
        if self.cfg.get("server", "proxy_user"):
            self.xml.get_widget("enableProxyAuthButton").set_active(True)

        self.enableAction(self.xml.get_widget("enableProxyAuthButton"))
        self.enableAction(self.xml.get_widget("enableProxyButton"))

        # the extra or "" are to make sure we don't str None
        self.xml.get_widget("proxyUserEntry").set_text(str(self.cfg.get("server", "proxy_user") or ""))
        self.xml.get_widget("proxyPasswordEntry").set_text(str(self.cfg.get("server", "proxy_password") or ""))
        self.xml.get_widget("connectionStatusLabel").set_label("")
        # If there is no proxy information, disable the proxy test
        # button.
        if not self.xml.get_widget("enableProxyButton").get_active():
            self.xml.get_widget("testConnectionButton").set_sensitive(False)

    def writeValues(self, widget=None, dummy=None):
        proxy = self.xml.get_widget("proxyEntry").get_text() or ""

        # don't save these values if they are disabled in the gui
        if proxy and self.xml.get_widget("enableProxyButton").get_active():
            # Remove any URI scheme provided
            proxy = remove_scheme(proxy)
            # Update the proxy entry field to show we removed any scheme
            self.xml.get_widget("proxyEntry").set_text(proxy)
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

        if self.xml.get_widget("enableProxyAuthButton").get_active():
            if self.xml.get_widget("proxyUserEntry").get_text() is not None:
                self.cfg.set("server", "proxy_user",
                             str(self.xml.get_widget("proxyUserEntry").get_text()))

            if self.xml.get_widget("proxyPasswordEntry").get_text() is not None:
                self.cfg.set("server", "proxy_password",
                             str(self.xml.get_widget("proxyPasswordEntry").get_text()))
        else:
            self.cfg.set("server", "proxy_user", "")
            self.cfg.set("server", "proxy_password", "")

        try:
            self.cfg.save()
        except:
            errorWindow(_("There was an error saving your configuration.") +
                    _("Make sure that you own %s.") % self.cfg.fileName,
                    parent=self.dlg)

    def show(self):
        self.setInitialValues()
        self.dlg.present()

    def close(self, button):
        self.writeValues()
        self.dlg.hide()

    def enableTestButton(self, button):
        test_connection_button = self.xml.get_widget("testConnectionButton")
        test_connection_button.set_sensitive(button.get_active())

    def clearConnectionLabel(self, entry):
        self.xml.get_widget("connectionStatusLabel").set_label("")

    def displayConnectionStatus(self, button):
        connection_label = self.xml.get_widget("connectionStatusLabel")
        if self.testConnection():
            connection_label.set_label(_("Proxy connection succeeded"))
        else:
            connection_label.set_label(_("Proxy connection failed"))

    def testConnection(self):
        proxy_host = remove_scheme(self.cfg.get("server", "proxy_hostname"))
        proxy_port = self.cfg.get("server", "proxy_port")
        proxy_user = self.cfg.get("server", "proxy_user")
        proxy_password = self.cfg.get("server", "proxy_password")

        server_host = self.cfg.get("server", "hostname")
        server_port = self.cfg.get("server", "port")
        server_prefix = self.cfg.get("server", "prefix")

        cp = connection.UEPConnection(host=server_host,
                                    ssl_port=server_port,
                                    handler=server_prefix,
                                    proxy_hostname=proxy_host,
                                    proxy_port=proxy_port,
                                    proxy_user=proxy_user,
                                    proxy_password=proxy_password,
                                    username=None,
                                    password=None,
                                    cert_file=None,
                                    key_file=None
                                    )
        try:
            cp.getStatus()
        except connection.RemoteServerException, e:
            log.debug("Reporting proxy connection as good despite %s" % \
                        e.code)
            return True
        except connection.RestlibException, e:
            log.debug("Reporting proxy connection as good despite %s" % \
                        e.code)
            return True
        except connection.NetworkException, e:
            log.debug("%s when attempting to connect through %s:%s" % \
                    (e.code, proxy_host, proxy_port))
            return False
        except Exception, e:
            log.debug("'%s' when attempting to connect through %s:%s" % \
                    (e, proxy_host, proxy_port))
            return False
        else:
            return True

    def deleted(self, event, data):
        self.writeValues()
        self.dlg.hide()
        return True

    def enableAction(self, button):
        if button.get_name() == "enableProxyButton":
            self.xml.get_widget("proxyEntry").set_sensitive(button.get_active())
            self.xml.get_widget("proxyEntry").grab_focus()
        elif button.get_name() == "enableProxyAuthButton":
            self.xml.get_widget("proxyUserEntry").set_sensitive(button.get_active())
            self.xml.get_widget("proxyPasswordEntry").set_sensitive(button.get_active())
            self.xml.get_widget("usernameLabel").set_sensitive(button.get_active())
            self.xml.get_widget("passwordLabel").set_sensitive(button.get_active())

    def set_parent_window(self, window):
        self.dlg.set_transient_for(window)
