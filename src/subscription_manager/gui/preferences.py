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

import os
import gettext
import gtk
import gtk.glade

import rhsm.config

from subscription_manager.gui.utils import errorWindow
from subscription_manager.gui.widgets import SubscriptionManagerTab

_ = gettext.gettext

DIR = os.path.dirname(__file__)
GLADE_XML = gtk.glade.XML(os.path.join(DIR, "data/preferences.glade"))


class PreferencesDialog(object):
    """
    Dialog for setting system preferences.

    Uses the instant apply paradigm or whatever you wanna call it that the
    gnome HIG recommends. Whenever a toggle button is flipped or a text entry
    changed, the new setting will be saved.
    """

    def __init__(self):
        widget_names = [
                'preferences_dialog',
                'sla_combobox',
            ]

        self.dialog = GLADE_XML.get_widget('preferences_dialog')
        self.sla_combobox = GLADE_XML.get_widget('sla_combobox')

        # Need to load values before connecting signals because when the dialog
        # starts up it seems to trigger the signals which overwrites the config
        # with the blank values.
        #self.setInitialValues()

        GLADE_XML.signal_autoconnect({
            "on_close_button_clicked": self._close_button_clicked,
        })

    def _close_button_clicked(self, widget):
        self.dialog.hide()

    def setInitialValues(self):
        pass

    def show(self):
        self.dialog.present()
