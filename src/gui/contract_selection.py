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

import os
import gobject
import gtk
import gtk.glade
import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)
import managerlib
import widgets

prefix = os.path.dirname(__file__)
CONTRACT_SELECTION_GLADE = os.path.join(prefix, "data/contract_selection.glade")


class ContractSelectionWindow(object):

    def __init__(self, selected_callback, cancel_callback):
        self._selected_callback = selected_callback
        self._cancel_callback = cancel_callback
        self.total_contracts = 0
        self.contract_selection_xml = gtk.glade.XML(CONTRACT_SELECTION_GLADE)
        self.contract_selection_win = self.contract_selection_xml.get_widget(
            "contract_selection_window")

        self.contract_selection_treeview = \
                self.contract_selection_xml.get_widget(
                        "contract_selection_treeview")

        self.subscription_name_label = self.contract_selection_xml.get_widget(
            "subscription_name_label")

        self.total_contracts_label = self.contract_selection_xml.get_widget(
            "total_contracts_label")

        self.contract_selection_xml.signal_autoconnect({
            "on_cancel_button_clicked": self._cancel_button_clicked,
            "on_subscribe_button_clicked": self._subscribe_button_clicked,
        })

        self.model = gtk.ListStore(str, str, str, str, str,
                gobject.TYPE_PYOBJECT)
        self.contract_selection_treeview.set_model(self.model)

    def show(self):
        self.populate_treeview()
        self.contract_selection_win.show_all()

    def destroy(self):
        self.contract_selection_win.destroy()

    def populate_treeview(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Contract Number"), renderer, text=0)
        self.contract_selection_treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Contracts Used / Available"), renderer,
                text=1)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(_("Start Date"), renderer, text=2)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(_("Expiration Date"), renderer, text=3)
        self.contract_selection_treeview.append_column(column)

    def add_pool(self, pool):
        self.total_contracts += int(pool['quantity'])
        self.total_contracts_label.set_text(str(self.total_contracts))
        self.subscription_name_label.set_text(pool['productName'])

        row = [pool['productId'],
                "%s / %s" % (pool['consumed'], pool['quantity']),
                pool['startDate'], pool['endDate'], pool['productName'], pool]
        self.model.append(row)
    
    def _cancel_button_clicked(self, button):
        self._cancel_callback()

    def _subscribe_button_clicked(self, button):
        self._selected_callback(
                self.model[self.contract_selection_treeview.get_cursor()[0][0]][5])
