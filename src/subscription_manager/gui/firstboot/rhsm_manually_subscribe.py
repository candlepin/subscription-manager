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
        # Firstboot module title
        # Note: translated title needs to be unique across all
        # firstboot modules, not just the rhsm ones. See bz #828042
                _("Manual Configuration Required"),
                _("Subscription Registration"),
                200.2, 109.11)

        self.screen = get_screen()

    def apply(self, interface, testing=False):
        # Clicking Next always proceeds to the next screen.
        self._skip_remaining_screens(interface)
        return self._RESULT_JUMP

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self.screen.content_container.reparent(self.vbox)

    def initializeUI(self):
        self.vbox.show_all()


# for el5
childWindow = moduleClass
