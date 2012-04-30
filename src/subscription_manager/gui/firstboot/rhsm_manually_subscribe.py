#
# GUI Module for the Autobind Wizard
#
# Copyright (c) 2012 Red Hat, Inc.
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

import sys
import gtk

from firstboot.constants import RESULT_JUMP
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

sys.path.append("/usr/share/rhsm")
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.gui.manually_subscribe import get_screen


class moduleClass(Module):

    def __init__(self):
        Module.__init__(self)

        self.priority = 200.2
        self.sidebarTitle = _("Entitlement Registration")
        self.title = _("Manual Configuraton Required")

        self.screen = get_screen()

    def apply(self, interface, testing=False):
        # Clicking Next always proceeds to the next screen.
        self._skip_sla_screens(interface)
        return RESULT_JUMP

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self.screen.content_container.reparent(self.vbox)

    def initializeUI(self):
        self.vbox.show_all()

    def needsNetwork(self):
        return False

    def shouldAppear(self):
        """
        Indicates to firstboot whether to show this screen.  In this case
        we want to skip over this screen if there is already an identity
        certificate on the machine (most likely laid down in a kickstart).
        """
        return not ConsumerIdentity.existsAndValid()

    def _skip_sla_screens(self, interface):
        """
        Find the first non rhsm module after the rhsm modules, and move to it.

        Assumes that only our modules are grouped together, and that we have
        4.
        """
        i = 0
        while not interface.moduleList[i].__module__.startswith('rhsm_'):
            i += 1
        interface.moveToPage(pageNum=i + 4)
