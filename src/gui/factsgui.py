#
# GUI Module for standalone subscription-manager - System Facts Dialog
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Justin Harris <jharris@redhat.com>
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
import gtk

import connection
import facts
import managergui

import logutil
log = logutil.getLogger(__name__)

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/factsdialog.glade")

def _add_column(name, order):
    return gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)

class SystemFactsDialog:

    def __init__(self):
        glade = gtk.glade.XML(GLADE_XML)
        glade.signal_autoconnect({
                "on_system_facts_dialog_delete_event" : self.hide,
                "on_close_button_clicked" : self.hide,
                "on_facts_update_button_clicked" : self.update_facts
                })

        self.dialog = glade.get_widget("system_facts_dialog")
        self.facts_view = glade.get_widget("system_facts_view")
        self.update_button = glade.get_widget("update_facts_button")

        # Set up the model
        self.facts_store = gtk.ListStore(str, str)
        self.facts_view.set_model(self.facts_store)

        # Set up columns on the view
        self.facts_view.append_column(_add_column("Fact", 0))
        self.facts_view.append_column(_add_column("Value", 1))

        # Update the displayed facts
        self.display_facts()

    def show(self):
        # Disable the 'Update' button if there is
        # no registered consumer to update
        self.update_button.set_sensitive(bool(managergui.consumer))
        self.dialog.present()

    def hide(self, button, event=None):
        self.dialog.hide()

        return True

    def display_facts(self):
        self.facts_store.clear()

        system_facts = facts.getFacts()
        for fact, value in system_facts.get_facts().items():
            self.facts_store.append([fact, value])

    def update_facts(self, button):
        system_facts = facts.getFacts()
        consumer = managergui.consumer['uuid']

        try:
            managergui.UEP.updateConsumerFacts(consumer, system_facts.get_facts())
        except connection.RestlibException, e:
            log.error("Could not update system facts:  error %s" % ( e))
            managergui.errorWindow(managergui.linkify(e.msg))
        except Exception, e:
            log.error("Could not update system facts \nError: %s" % (e))
            managergui.errorWindow(managergui.linkify(e.msg))

