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

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui.manually_subscribe import get_screen
from subscription_manager.gui.firstboot_base import RhsmFirstbootModule


class moduleClass(RhsmFirstbootModule):

    def __init__(self):
        RhsmFirstbootModule.__init__(self,
                _("Manual Configuration Required"),
                _("Entitlement Registration"),
                200.2, 109.11)

        self.screen = get_screen()

    def apply(self, interface, testing=False):
        # Clicking Next always proceeds to the next screen.
        self._skip_sla_screens(interface)
        return self._RESULT_JUMP

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self.screen.content_container.reparent(self.vbox)

    def initializeUI(self):
        self.vbox.show_all()

    def _skip_sla_screens(self, interface):
        """
        Find the first non rhsm module after the rhsm modules, and move to it.

        Assumes that only our modules are grouped together, and that we have
        4.
        """

        if self._is_compat:
            # must be el5, need to use self.parent to get the moduleList
            interface = self.parent

        i = 0
        while not interface.moduleList[i].__module__.startswith('rhsm_'):
            i += 1

        i += 4

        # el5 compat. depends on this being called from apply,
        # interface = self.parent
        # and apply returning true
        if self._is_compat:
            self.parent.nextPage = i
        else:
            interface.moveToPage(pageNum=i)


# for el5
childWindow = moduleClass
