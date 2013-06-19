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

import gettext
import logging
import os

import gtk
import gtk.glade

from subscription_manager.injection import require, IDENTITY
from subscription_manager import release

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

    def __init__(self, backend, parent):

        self.backend = backend
        self.identity = require(IDENTITY)
        self.release_backend = release.ReleaseBackend(ent_dir=self.backend.entitlement_dir,
                                                      prod_dir=self.backend.product_dir,
                                                      content_connection=self.backend.content_connection,
                                                      uep=self.backend.cp_provider.get_consumer_auth_cp())

        self.dialog = GLADE_XML.get_widget('preferences_dialog')
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)

        self.release_combobox = GLADE_XML.get_widget('release_combobox')
        self.sla_combobox = GLADE_XML.get_widget('sla_combobox')

        # The first string is the displayed service level; the second is
        # the value sent to Candlepin.
        self.release_model = gtk.ListStore(str, str)
        self.sla_model = gtk.ListStore(str, str)

        self.release_combobox.set_model(self.release_model)
        self.sla_combobox.set_model(self.sla_model)

        GLADE_XML.signal_autoconnect({
            "on_close_button_clicked": self._close_button_clicked,
            "on_sla_combobox_changed": self._sla_changed,
            "on_release_combobox_changed": self._release_changed,
        })

        # Handle the dialog's delete event when ESC key is pressed.
        self.dialog.connect("delete-event", self._dialog_deleted)

    def load_current_settings(self):
        self.sla_combobox.get_model().clear()
        self.release_combobox.get_model().clear()

        if self.identity.uuid is None:
            self.sla_combobox.set_sensitive(False)
            self.release_combobox.set_sensitive(False)
            return

        self.sla_combobox.set_sensitive(True)
        self.release_combobox.set_sensitive(True)

        consumer_json = self.backend.cp_provider.get_consumer_auth_cp().getConsumer(self.identity.uuid)

        self.load_releases(consumer_json)
        self.load_servicelevel(consumer_json)

    def load_servicelevel(self, consumer_json):
        # The combo box you get from the widget tree already has a
        # CellRendererText that renders the first column in the ListStore. If
        # you needed to change the ListStore column used you would write:
        #    combo.set_attribute(combo.get_cells()[0], 'text', column_number)

        if 'serviceLevel' not in consumer_json:
            log.warn("Disabling service level dropdown, server does not support service levels.")
            self.sla_combobox.set_sensitive(False)
            return

        current_sla = consumer_json['serviceLevel']
        owner_key = consumer_json['owner']['key']
        available_slas = self.backend.cp_provider.get_consumer_auth_cp().getServiceLevelList(owner_key)

        # An empty string entry is used for "un-setting" the system's SLA:
        self.sla_model.append((_("Not Set"), ""))
        available_slas.insert(0, "")

        i = 0
        for sla in available_slas:
            if sla:
                self.sla_model.append((sla, sla))
            if sla.lower() == current_sla.lower():
                self.sla_combobox.set_active(i)
            i += 1

    def load_releases(self, consumer_json):
        if "releaseVer" not in consumer_json:
            log.warn("Disabling release version  dropdown, server does not support release versions.")
            self.release_combobox.set_sensitive(False)
            return

        self.release_combobox.set_sensitive(True)
        current_release = None
        if consumer_json['releaseVer']:
            current_release = consumer_json['releaseVer']['releaseVer']

        available_releases = self.release_backend.get_releases()
        # current release might not be in the release listing
        if current_release and current_release not in available_releases:
            available_releases.insert(0, current_release)

        # for unsetting
        self.release_model.append((_("Not Set"), ""))
        available_releases.insert(0, "")
        self.release_combobox.set_active(0)

        i = 0
        for available_release in available_releases:
            if available_release:
                self.release_model.append((available_release, available_release))
            if available_release == current_release:
                self.release_combobox.set_active(i)
            i += 1

    def _close_button_clicked(self, widget):
        self._close_dialog()

    def _sla_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            log.info("SLA changed but nothing selected? Ignoring.")
            return

        new_sla = model[active][1]
        log.info("SLA changed to: %s" % new_sla)
        self.backend.cp_provider.get_consumer_auth_cp().updateConsumer(self.identity.uuid,
                                        service_level=new_sla)

    def _release_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            log.info("release changed but nothing selected? Ignoring.")
            return
        new_release = model[active][1]
        log.info("release changed to: %s" % new_release)
        self.backend.cp_provider.get_consumer_auth_cp().updateConsumer(self.identity.uuid,
                                        release=new_release)

    def show(self):
        self.load_current_settings()
        self.dialog.show()

    def _close_dialog(self):
        self.dialog.hide()

    def _dialog_deleted(self, event, data):
        self._close_dialog()
        return True
