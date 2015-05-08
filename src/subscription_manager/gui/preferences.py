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

from subscription_manager import ga
from subscription_manager.gui import widgets
from subscription_manager.gui import utils
from subscription_manager import injection as inj
from subscription_manager import release

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class PreferencesDialog(widgets.SubmanBaseWidget):
    """
    Dialog for setting system preferences.

    Uses the instant apply paradigm or whatever you wanna call it that the
    gnome HIG recommends. Whenever a toggle button is flipped or a text entry
    changed, the new setting will be saved.
    """

    widget_names = ['dialog', 'release_combobox', 'sla_combobox',
                    'autoheal_checkbox', 'autoheal_event', 'autoheal_label',
                    'close_button']
    gui_file = "preferences.glade"

    def __init__(self, backend, parent):
        super(PreferencesDialog, self).__init__()
        self.backend = backend
        self.allow_callbacks = False
        self.identity = inj.require(inj.IDENTITY)
        self.async_updater = utils.AsyncWidgetUpdater(self.dialog)
        self.release_backend = release.ReleaseBackend()

        self.inputs = [self.sla_combobox, self.release_combobox,
                self.autoheal_checkbox, self.autoheal_event]

        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)

        # The first string is the displayed service level; the second is
        # the value sent to Candlepin.
        self.release_model = ga.Gtk.ListStore(str, str)
        self.sla_model = ga.Gtk.ListStore(str, str)

        self.release_combobox.set_model(self.release_model)
        self.sla_combobox.set_model(self.sla_model)

        self.close_button.connect("clicked", self._close_button_clicked)
        self.sla_combobox.connect("changed", self._sla_changed)
        self.release_combobox.connect("changed", self._release_changed)
        self.autoheal_checkbox.connect("toggled", self._on_autoheal_checkbox_toggled)
        self.autoheal_event.connect("button_press_event", self._on_autoheal_label_press)

        # Handle the dialog's delete event when ESC key is pressed.
        self.dialog.connect("delete-event", self._dialog_deleted)

    def set_inputs_sensitive(self, sensitive):
        for input_widget in self.inputs:
            input_widget.set_sensitive(sensitive)

    def load_current_settings(self):
        self.sla_combobox.get_model().clear()
        self.release_combobox.get_model().clear()

        if self.identity.uuid is None:
            self.set_inputs_sensitive(False)
            return

        update = utils.WidgetUpdate(self.dialog)
        method = self.backend.cp_provider.get_consumer_auth_cp().getConsumer
        self.async_updater.update(update, method,
                args=[self.identity.uuid], callback=self.load_from_consumer_json)

    def load_from_consumer_json(self, consumer_json):
        self.allow_callbacks = False
        self.load_releases(consumer_json)
        self.load_servicelevel(consumer_json)
        self.load_autoheal(consumer_json)
        self.allow_callbacks = True

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

        for index, sla in enumerate(available_slas):
            if sla:
                self.sla_model.append((sla, sla))
            if sla.lower() == current_sla.lower():
                self.sla_combobox.set_active(index)

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

        for index, available_release in enumerate(available_releases):
            if available_release:
                self.release_model.append((available_release, available_release))
            if available_release == current_release:
                self.release_combobox.set_active(index)

    def load_autoheal(self, consumer_json):
        if 'autoheal' not in consumer_json:
            log.warn("Disabling auto-attach checkbox, server does not support autoheal/auto-attach.")
            self.autoheal_checkbox.set_sensitive(False)
            self.autoheal_event.set_sensitive(False)
            return

        self.autoheal_event.set_sensitive(True)
        self.autoheal_checkbox.set_sensitive(True)
        current_autoheal = consumer_json['autoheal']
        self.autoheal_checkbox.set_active(current_autoheal)

    def _close_button_clicked(self, widget):
        self._close_dialog()

    def _sla_changed(self, combobox):
        if self.allow_callbacks:
            model = combobox.get_model()
            active = combobox.get_active()
            if active < 0:
                log.info("SLA changed but nothing selected? Ignoring.")
                return

            new_sla = model[active][1]
            log.info("SLA changed to: %s" % new_sla)
            update = utils.WidgetUpdate(combobox)
            method = self.backend.cp_provider.get_consumer_auth_cp().updateConsumer
            self.async_updater.update(update, method, args=[self.identity.uuid], kwargs={'service_level': new_sla})

    def _release_changed(self, combobox):
        if self.allow_callbacks:
            model = combobox.get_model()
            active = combobox.get_active()
            if active < 0:
                log.info("release changed but nothing selected? Ignoring.")
                return
            new_release = model[active][1]
            log.info("release changed to: %s" % new_release)
            update = utils.WidgetUpdate(combobox)
            method = self.backend.cp_provider.get_consumer_auth_cp().updateConsumer
            self.async_updater.update(update, method, args=[self.identity.uuid], kwargs={'release': new_release})

    def show(self):
        self.load_current_settings()
        self.dialog.show()

    def _close_dialog(self):
        self.dialog.hide()

    def _dialog_deleted(self, event, data):
        self._close_dialog()
        return True

    def _on_autoheal_checkbox_toggled(self, checkbox):
        if self.allow_callbacks:
            log.info("Auto-attach preference changed to: %s" % checkbox.get_active())
            update = utils.WidgetUpdate(checkbox, self.autoheal_label)
            method = self.backend.cp_provider.get_consumer_auth_cp().updateConsumer
            self.async_updater.update(update, method, args=[self.identity.uuid], kwargs={'autoheal': checkbox.get_active()})
            return True

    def _on_autoheal_label_press(self, widget, event):
        # NOTE: We have this function/event so the textbox label
        #       next to the checkbox can be clicked, then trigger
        #       the checkbox
        if self.autoheal_checkbox.props.sensitive:
            self.autoheal_checkbox.set_active(not self.autoheal_checkbox.get_active())
        return True
