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
import logging

import rhsm.config

from subscription_manager.gui.utils import errorWindow
from subscription_manager.gui.widgets import SubscriptionManagerTab

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

DIR = os.path.dirname(__file__)
GLADE_XML = gtk.glade.XML(os.path.join(DIR, "data/preferences.glade"))


class PreferencesDialog(object):
    """
    Dialog for setting system preferences.

    Uses the instant apply paradigm or whatever you wanna call it that the
    gnome HIG recommends. Whenever a toggle button is flipped or a text entry
    changed, the new setting will be saved.
    """

    def __init__(self, backend, consumer):

        self.backend = backend
        self.consumer = consumer

        self.dialog = GLADE_XML.get_widget('preferences_dialog')
        self.sla_combobox = GLADE_XML.get_widget('sla_combobox')

        self.load_current_settings()

        GLADE_XML.signal_autoconnect({
            "on_close_button_clicked": self._close_button_clicked,
            "on_sla_combobox_changed": self._sla_changed,
        })

    def load_current_settings(self):
        self.sla_combobox.get_model().clear()
        consumer_json = self.backend.uep.getConsumer(self.consumer.uuid)
        current_sla = consumer_json['serviceLevel']
        owner_key = consumer_json['owner']['key']
        available_slas = self.backend.uep.getServiceLevelList(owner_key)

        # An empty string entry is available for "un-setting" the system's SLA:
        available_slas.insert(0, "")

        i = 0
        for sla in available_slas:
            self.sla_combobox.append_text(sla)
            if sla == current_sla:
                self.sla_combobox.set_active(i)
            i += 1

    def _close_button_clicked(self, widget):
        self.dialog.hide()

    def _sla_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            log.info("SLA changed but nothing selected? Ignoring.")
            return

        new_sla = model[active][0]
        log.info("SLA changed to: %s" % new_sla)
        self.backend.uep.updateConsumer(self.consumer.uuid,
                service_level=new_sla)

    def show(self):
        self.load_current_settings()
        self.dialog.show()
