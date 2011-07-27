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
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.gui.widgets import MachineTypeColumn
_ = gettext.gettext

from subscription_manager.gui import widgets
from subscription_manager.quantity import allows_multi_entitlement
from subscription_manager import managerlib

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
        self.contract_selection_treeview.get_selection().connect("changed",
            self._on_contract_selection)

        self.subscription_name_label = self.contract_selection_xml.get_widget(
            "subscription_name_label")

        self.total_contracts_label = self.contract_selection_xml.get_widget(
            "total_contracts_label")

        self.contract_selection_xml.signal_autoconnect({
            "on_cancel_button_clicked": self._cancel_button_clicked,
            "on_subscribe_button_clicked": self._subscribe_button_clicked,
        })

        self.quantity_renderer = gtk.CellRendererSpin()
        self.quantity_renderer.set_property("adjustment",
            gtk.Adjustment(lower=1, upper=100, step_incr=1))
        self.quantity_renderer.set_property("editable", True)
        self.quantity_renderer.connect("edited", self._on_quantity_change)

        self.model = gtk.ListStore(str, str,
                                   gobject.TYPE_PYOBJECT,
                                   gobject.TYPE_PYOBJECT,
                                   int,
                                   str,
                                   gobject.TYPE_PYOBJECT,
                                   bool)
        self.contract_selection_treeview.set_model(self.model)

    def show(self):
        self.populate_treeview()
        self.contract_selection_win.show_all()

    def destroy(self):
        self.contract_selection_win.destroy()

    def populate_treeview(self):

        column = MachineTypeColumn(_("Contract Number"), 7, 0)
        self.contract_selection_treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Used / Available"), renderer,
                text=1)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(_("Start Date"), renderer, date=2)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(_("End Date"), renderer, date=3)
        self.contract_selection_treeview.append_column(column)

        column = gtk.TreeViewColumn(_("Quantity"), self.quantity_renderer, text=4)
        self.contract_selection_treeview.append_column(column)

    def add_pool(self, pool, default_quantity_value):
        self.total_contracts += 1
        self.total_contracts_label.set_text(str(self.total_contracts))
        self.subscription_name_label.set_text(pool['productName'])

        # Use unlimited for -1 quanities
        quantity = pool['quantity']
        if quantity < 0:
            quantity = _('unlimited')

        row = [pool['contractNumber'],
                "%s / %s" % (pool['consumed'], quantity),
               managerlib.parseDate(pool['startDate']),
               managerlib.parseDate(pool['endDate']),
               default_quantity_value,
               pool['productName'], pool,
               PoolWrapper(pool).is_virt_only()]
        self.model.append(row)

    def set_parent_window(self, window):
        self.contract_selection_win.set_transient_for(window)

    def _cancel_button_clicked(self, button):
        self._cancel_callback()

    def _subscribe_button_clicked(self, button):
        row = self.model[self.contract_selection_treeview.get_cursor()[0][0]]
        pool = row[6]
        quantity = row[4]
        self._selected_callback(pool, quantity)

    def _on_quantity_change(self, renderer, path, new_text):
        """ Handles when a quantity is changed in the cell """
        try:
            new_quantity = int(new_text)
            iter = self.model.get_iter(path)
            self.model.set_value(iter, 4, new_quantity)
        except ValueError, e:
            # Do nothing... The value entered in the grid will be reset.
            pass

    def _on_contract_selection(self, widget):
        model, tree_iter = widget.get_selected()

        # Handle no selection in table.
        if not tree_iter:
            return

        row = model[tree_iter]
        pool = row[6]

        # Only enable quantity if subscription is multi-entitlement capable
        self.quantity_renderer.set_property("editable", allows_multi_entitlement(pool))
