#
# Copyright (C) 2015  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

import logging
import sys

from pyanaconda.ui.gui.spokes import NormalSpoke
from pyanaconda.ui.common import FirstbootOnlySpokeMixIn
from pyanaconda.ui.gui.categories.system import SystemCategory

# need sys.path?

log = logging.getLogger(__name__)

#from gi.repository import Gtk
#from gi.repository from gi.repository import Gtk

log.debug("sys.path=%s", sys.path)
from subscription_manager.gui import managergui
from subscription_manager.injectioninit import init_dep_injection
#from subscription_manager.injection import PLUGIN_MANAGER, IDENTITY, require
from subscription_manager.gui import registergui

# FIXME

__all__ = ["RHSMSpoke"]


class RHSMSpoke(FirstbootOnlySpokeMixIn, NormalSpoke):
    buildrObjects = ["RHSMSpokeWindow"]

    mainWidgetName = "RHSMSpokeWindow"

    uiFile = "rhsm_gui.glade"

    category = SystemCategory

    icon = "face-cool-symbolic"

    title = "Subscription Manager"

    def __not_init__(self, data, storage, payload, instclass):
        log.debug("I've been __init__()'ed")
        NormalSpoke.__init__(self, data, storage, payload, instclass)
        log.debug("data %s", repr(self.data))
        log.debug("storage %s", self.storage)
        log.debug("payload %s", self.payload)
        log.debug("instclass %s", self.instclass)
        self._done = False

    def initialize(self):
        log.debug("I've been initialize()'ed")
        NormalSpoke.initialize(self)
        self._done = False
        init_dep_injection()
        backend = managergui.Backend()
        log.debug("backend=%s", backend)

        self.registergui = registergui.RegisterScreen(backend)

    def run(self):
        log.debug("run")
        self.registergui.window.show()
        rc = self.registergui.window.run()
        self.registergui.window.hide()

        return rc

    def refresh(self):
        pass

    def apply(self):
        log.debug("help me, I'm being apply()'ed")
        self.data.addons.com_redhat_subscription_manager.text = "applied! yay!"

    def execute(self):
        log.debug("execute() is not a good method to anthropomorphize")

    @property
    def ready(self):
        log.debug(" READY")
        return True

    @property
    def completed(self):
        log.info("completed")
        #return bool(self._done)
        return True

    @property
    def mandatory(self):
        return False

    @property
    def status(self):
        return "Likely not working."

    def on_big_button_activate(self, button, *args):
        log.debug("big button was _A_ctivated, now preparing to do  absolutely nothing. %s", args)

    def on_big_button_clicked(self, button, *args):
        self._done = True
        log.debug("big button was clicked, now doing absolutely nothing. %s %s", button, args)
        log.debug("self %s, self._done %s", self, self._done)
