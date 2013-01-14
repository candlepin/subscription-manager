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

import logging
import gtk

from subscription_manager.gui.utils import linkify, handle_gui_exception
from subscription_manager.gui import widgets
from subscription_manager.managerlib import enhance_facts

import gettext
_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class SystemFactsDialog(widgets.GladeWidget):
    """GTK dialog for displaying the current system facts, as well as
    providing functionality to update the UEP server with the current
    system facts.
    """
    widget_names = ['system_facts_dialog', 'facts_view', 'update_button',
                    'last_update_label', 'owner_label', 'environment_label',
                    'environment_hbox', 'owner_id_label', 'owner_id_hbox']

    def __init__(self, backend, consumer, facts):

        super(SystemFactsDialog, self).__init__('factsdialog.glade')

        self.consumer = consumer
        self.facts = facts
        self.backend = backend
        self.glade.signal_autoconnect({
                "on_system_facts_dialog_delete_event": self._hide_callback,
                "on_close_button_clicked": self._hide_callback,
                "on_facts_update_button_clicked": self._update_facts_callback
                })

        # Set up the model
        self.facts_store = gtk.TreeStore(str, str)
        self.facts_view.set_model(self.facts_store)

        # Set up columns on the view
        self._add_column(_("Fact"), 0)
        self._add_column(_("Value"), 1)

        # set up the signals from the view
        self.facts_view.connect("row_activated",
                        widgets.expand_collapse_on_row_activated_callback)

    def show(self):
        """Make this dialog visible."""
        # Disable the 'Update' button if there is
        # no registered consumer to update

        # Update the displayed facts
        self.display_facts()

        # Set sorting by fact name
        self.facts_store.set_sort_column_id(0, gtk.SORT_ASCENDING)

        self.update_button.set_sensitive(bool(self.consumer.uuid))
        self.system_facts_dialog.present()

    def hide(self):
        """Make this dialog invisible."""
        self.system_facts_dialog.hide()

    def display_facts(self):
        """Updates the list store with the current system facts."""
        self.facts_store.clear()

        last_update = self.facts.get_last_update()
        if last_update:
            self.last_update_label.set_text(last_update.strftime("%c"))
        else:
            self.last_update_label.set_text(_('No previous update'))

        # make sure we get fresh facts, since entitlement validity status could         # change
        system_facts_dict = self.facts.get_facts()

        enhance_facts(system_facts_dict, self.consumer)
        system_facts = system_facts_dict.items()

        system_facts.sort()
        group = None
        for fact, value in system_facts:
            new_group = fact.split(".", 1)[0]
            if new_group != group:
                group = new_group
                parent = self.facts_store.append(None, [group, ""])
            if str(value).strip() == "":
                value = _("Unknown")
            self.facts_store.append(parent, [fact, value])

        # TODO: could stand to check if registered before trying to do this:
        displayName = _('Unknown')
        try:
            owner = self.backend.uep.getOwner(self.consumer.uuid)
            displayName = owner['displayName']
            key = owner['key']
            self.owner_id_label.set_text(key)
            self.owner_id_hbox.show()
        except Exception, e:
            log.error("Could not get owner name \nError: %s" % e)
            self.owner_id_hbox.hide()
        self.owner_label.set_text(displayName)

        try:
            if self.backend.uep.supports_resource('environments'):
                consumer = self.backend.uep.getConsumer(self.consumer.uuid)
                environment = consumer['environment']
                if environment:
                    environment_name = environment['name']
                else:
                    environment_name = _("None")

                log.info("Environment is %s" % environment_name)
                self.environment_label.set_text(environment_name)
                self.environment_hbox.show()
            else:
                self.environment_hbox.hide()
        except Exception, e:
            log.error("Could not get environment \nError: %s" % e)
            self.environment_hbox.hide()

    def update_facts(self):
        """Sends the current system facts to the UEP server."""
        consumer_uuid = self.consumer.uuid

        try:
            self.facts.update_check(self.backend.uep, consumer_uuid, force=True)
        except Exception, e:
            log.error("Could not update system facts \nError: %s" % e)
            handle_gui_exception(e, linkify(str(e)), self.system_facts_dialog)

    # GTK callback function for hiding this dialog.
    def _hide_callback(self, button, event=None):
        self.hide()

        # Stop the gtk signal from propogating
        return True

    # GTK callback function for sending system facts to the server
    def _update_facts_callback(self, button):
        self.update_facts()
        self.display_facts()

    def _add_column(self, name, order):
        """Adds a gtk.TreeViewColumn suitable for displaying text to
        the facts gtk.TreeView.

        @type   name: string
        @param  name: The name of the created column
        @type  order: integer
        @param order: The 0-based index of the created column
        (in relation to other columns)
        """
        column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)
        self.facts_view.append_column(column)

    def set_parent_window(self, window):
        self.system_facts_dialog.set_transient_for(window)
