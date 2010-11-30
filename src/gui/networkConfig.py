
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
import config

import os
import gtk

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/networkConfig.glade")

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

        self.cfg = config.initConfig()
#        try:
#            self.cfg = config.initUp2dateConfig()
#        except:
#            gnome.ui.GnomeErrorDialog(_("There was an error loading your "
#                                        "configuration.  Make sure that\nyou "
#                                        "have read access to /etc/sysconfig/rhn."),
#                                      self.dlg)
        # Need to load values before connecting signals because when the dialog 
        # starts up it seems to trigger the signals which overwrites the config 
        # with the blank values.
        self.setInitialValues()
        self.enableProxyButton.connect("toggled", self.enableAction)
        self.enableProxyAuthButton.connect("toggled", self.enableAction)
        self.enableProxyButton.connect("toggled", self.writeValues)
        self.enableProxyAuthButton.connect("toggled", self.writeValues)
        self.proxyEntry.connect("focus-out-event", self.writeValues)
        self.proxyUserEntry.connect("focus-out-event", self.writeValues)
        self.proxyPasswordEntry.connect("focus-out-event", self.writeValues)
        self.xml.get_widget("closeButton").connect("clicked", self.close)
    
    def setInitialValues(self):
       
        self.xml.get_widget("proxyEntry").set_text("%s:%s" % (self.cfg.get("server", "proxy_hostname"),
                                                              self.cfg.get("server", "proxy_port")))
        if self.cfg.get("server", "proxy_hostname"):
            self.xml.get_widget("enableProxyButton").set_active(True)
        if self.cfg.get("server", "proxy_user"):
            self.xml.get_widget("enableProxyAuthButton").set_active(True)

        self.enableAction(self.xml.get_widget("enableProxyAuthButton"))
        self.enableAction(self.xml.get_widget("enableProxyButton"))
        self.xml.get_widget("proxyUserEntry").set_text(str(self.cfg.get("server", "proxy_user")))
        self.xml.get_widget("proxyPasswordEntry").set_text(str(self.cfg.get("server", "proxy_password")))
    
    def writeValues(self, widget=None, dummy=None):

        print "writeValues"
        proxy = self.xml.get_widget("proxyEntry").get_text()

        if proxy:
            # FIXME: this should probably be smarter
            proxy_hostname, proxy_port = proxy.split(':')
            self.cfg.set("server", "proxy_hostname", proxy_hostname)
            self.cfg.set("server", "proxy_port", proxy_port)

        if self.xml.get_widget("proxyUserEntry").get_text():
            self.cfg.set("server", "proxy_user",
                         str(self.xml.get_widget("proxyUserEntry").get_text()))

        if self.xml.get_widget("proxyPasswordEntry").get_text():
            self.cfg.set("server", "proxy_passwd",
                         str(self.xml.get_widget("proxyPasswordEntry").get_text()))
        
        try:
            self.cfg.save()
        except:
            gnome.ui.GnomeErrorDialog(_(
                    "There was an error saving your configuration. "\
                    "Make sure that\nyou own %s.") % self.cfg.fileName,
                                      self.dlg)
    
    def show(self):
        self.dlg.present()

    def close(self, button):
        self.dlg.hide()
    
    def enableAction(self, button):
        if button.get_name() == "enableProxyButton":
            self.xml.get_widget("proxyEntry").set_sensitive(button.get_active())
            self.xml.get_widget("proxyEntry").grab_focus()
        elif button.get_name() == "enableProxyAuthButton":
            self.xml.get_widget("proxyUserEntry").set_sensitive(button.get_active())
            self.xml.get_widget("proxyPasswordEntry").set_sensitive(button.get_active())
            self.xml.get_widget("usernameLabel").set_sensitive(button.get_active())
            self.xml.get_widget("passwordLabel").set_sensitive(button.get_active())
