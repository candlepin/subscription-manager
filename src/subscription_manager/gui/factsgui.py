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

import gettext
import logging

#from gi.repository import Gtk

from subscription_manager import ga
from subscription_manager.gui import widgets
from subscription_manager.gui.utils import handle_gui_exception, linkify
from subscription_manager import injection as inj

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class SystemFactsDialog(widgets.SubmanBaseWidget):
    """GTK dialog for displaying the current system facts, as well as
    providing functionality to update the UEP server with the current
    system facts.
    """
    widget_names = ['system_facts_dialog', 'facts_view', 'update_button',
                    'last_update_label', 'owner_label', 'owner_title',
                    'environment_label', 'environment_title',
                    'system_id_label', 'system_id_title']
    gui_file = "factsdialog.glade"

    def __init__(self, facts):

        super(SystemFactsDialog, self).__init__()

        #self.consumer = consumer
        self.identity = inj.require(inj.IDENTITY)
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.facts = facts
        self.connect_signals({
                "on_system_facts_dialog_delete_event": self._hide_callback,
                "on_close_button_clicked": self._hide_callback,
                "on_facts_update_button_clicked": self._update_facts_callback
                })

        # Set up the model
        self.facts_store = ga.Gtk.TreeStore(str, str)
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
        self.facts_store.set_sort_column_id(0, ga.Gtk.SortType.ASCENDING)

        self.update_button.set_sensitive(bool(self.identity.uuid))
        self.system_facts_dialog.present()

    def hide(self):
        """Make this dialog invisible."""
        self.system_facts_dialog.hide()

    def _display_system_id(self, identity):
        if identity.uuid:
            self.system_id_label.set_text(identity.uuid)
            self.system_id_title.show()
            self.system_id_label.show()
        else:
            self.system_id_label.set_text(_('Unknown'))
            self.system_id_title.hide()
            self.system_id_label.hide()

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

        system_facts = system_facts_dict.items()

        system_facts.sort()
        group = None
        for fact, value in system_facts:
            new_group = fact.split(".", 1)[0]
            if new_group != group:
                group = new_group
                parent = self.facts_store.append(None, [str(group), ""])
            if str(value).strip() == "":
                value = _("Unknown")
            self.facts_store.append(parent, [str(fact), str(value)])

        identity = inj.require(inj.IDENTITY)
        self._display_system_id(identity)

        # TODO: could stand to check if registered before trying to do this:
        #       all of the consumer auth cp calls should do that...
        # TODO: This would clean if we gather the info then updated the gui.
        #       These calls are not async atm so we block anyway
        try:
            owner = self.cp_provider.get_consumer_auth_cp().getOwner(identity.uuid)
            self.owner_label.set_text("%s (%s)" %
                    (owner['displayName'], owner['key']))
            self.owner_label.show()
            self.owner_title.show()
        # very broad exception
        except Exception, e:
            log.error("Could not get owner name: %s" % e)
            self.owner_label.hide()
            self.owner_title.hide()

        try:
            if self.cp_provider.get_consumer_auth_cp().supports_resource('environments'):
                consumer = self.cp_provider.get_consumer_auth_cp().getConsumer(identity.uuid)
                environment = consumer['environment']
                if environment:
                    environment_name = environment['name']
                else:
                    environment_name = _("None")

                log.info("Environment is %s" % environment_name)
                self.environment_label.set_text(environment_name)
                self.environment_label.show()
                self.environment_title.show()
            else:
                self.environment_label.hide()
                self.environment_title.hide()
        except Exception, e:
            log.error("Could not get environment \nError: %s" % e)
            self.environment_label.hide()
            self.environment_title.hide()

    def update_facts(self):
        """Sends the current system facts to the UEP server."""

        identity = inj.require(inj.IDENTITY)

        try:
            self.facts.update_check(self.cp_provider.get_consumer_auth_cp(), identity.uuid, force=True)
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
        """Adds a Gtk.TreeViewColumn suitable for displaying text to
        the facts Gtk.TreeView.

        @type   name: string
        @param  name: The name of the created column
        @type  order: integer
        @param order: The 0-based index of the created column
        (in relation to other columns)
        """
        column = ga.Gtk.TreeViewColumn(name, ga.Gtk.CellRendererText(), text=order)
        self.facts_view.append_column(column)

    def set_parent_window(self, window):
        self.system_facts_dialog.set_transient_for(window)
