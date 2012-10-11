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
import datetime
import time
import gobject
import gtk
import gtk.glade
import gettext
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.gui.widgets import MachineTypeColumn, MultiEntitlementColumn
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
        self.subscribe_button = self.contract_selection_xml.get_widget('subscribe_button')
        self.edit_quantity_label = self.contract_selection_xml.get_widget('edit_quantity_label')

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

        self.model = gtk.ListStore(str, str,
                                   gobject.TYPE_PYOBJECT,
                                   gobject.TYPE_PYOBJECT,
                                   int,
                                   str,
                                   gobject.TYPE_PYOBJECT,
                                   bool,
                                   bool,
                                   int)
        self.contract_selection_treeview.set_model(self.model)

    def show(self):
        self.populate_treeview()
        self.contract_selection_win.show_all()

    def destroy(self):
        self.contract_selection_win.destroy()

    def populate_treeview(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Contract"), renderer,
                text=0)
        column.set_expand(True)
        column.set_sort_column_id(0)
        self.model.set_sort_func(0, self._sort_text, None)
        self.contract_selection_treeview.append_column(column)

        column = MachineTypeColumn(7)
        column.set_sort_column_id(7)
        self.model.set_sort_func(7, self._sort_machine_type, column)
        self.contract_selection_treeview.append_column(column)

        renderer = gtk.CellRendererText()
        renderer.set_property("xalign", 0.5)
        column = gtk.TreeViewColumn(_("Used / Total"), renderer,
                text=1)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(_("Start Date"), renderer, date=2)
        column.set_sort_column_id(2)
        self.model.set_sort_func(2, self._sort_date, None)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(_("End Date"), renderer, date=3)
        column.set_sort_column_id(3)
        self.model.set_sort_func(3, self._sort_date, None)
        self.contract_selection_treeview.append_column(column)

        column = MultiEntitlementColumn(8)
        self.contract_selection_treeview.append_column(column)

        column = widgets.QuantitySelectionColumn(_("Quantity"), self.model, 4, 8, 9)
        self.contract_selection_treeview.append_column(column)

        self.edit_quantity_label.set_label(column.get_column_legend_text())

    def add_pool(self, pool, default_quantity_value):
        self.total_contracts += 1
        self.total_contracts_label.set_text(str(self.total_contracts))
        self.subscription_name_label.set_text(pool['productName'])

        # Use unlimited for -1 quanities
        quantity = pool['quantity']
        if quantity < 0:
            quantity = _('Unlimited')
            quantity_available = -1
        else:
            quantity_available = int(pool['quantity']) - int(pool['consumed'])

        # cap the default selected quantity at the max available
        # for that pool. See #855257
        if default_quantity_value > quantity_available:
            default_quantity_value = quantity_available

        row = [pool['contractNumber'],
                "%s / %s" % (pool['consumed'], quantity),
               managerlib.parseDate(pool['startDate']),
               managerlib.parseDate(pool['endDate']),
               default_quantity_value,
               pool['productName'], pool,
               PoolWrapper(pool).is_virt_only(),
               allows_multi_entitlement(pool),
               quantity_available]
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

    def _on_contract_selection(self, widget):
        model, tree_iter = widget.get_selected()

        enabled = True
        if not tree_iter:
            enabled = False

        self.subscribe_button.set_sensitive(enabled)

    def _sort_text(self, model, row1, row2, data):
        sort_column, sort_type = model.get_sort_column_id()
        str1 = model.get_value(row1, sort_column)
        str2 = model.get_value(row2, sort_column)
        return cmp(str1, str2)

    def _sort_machine_type(self, model, row1, row2, col):
        # Machine type is actually a boolean denoting whether the type is
        # virtual or not.  We do not want to sort on the boolean value.
        # Instead we want to sort on the text value that is going to get
        # displayed for the boolean value.
        sort_column, sort_type = model.get_sort_column_id()
        results = []
        for i, row in enumerate([row1, row2]):
            _bool = model.get_value(row, sort_column)
            if _bool is None:
                text = col._get_none_text()
            elif bool(_bool):
                text = col._get_true_text()
            else:
                text = col._get_false_text()
            results.append(text)
        return cmp(results[0], results[1])

    def _sort_date(self, model, row1, row2, data):
        """
        Used for sorting dates that could be None.
        """
        sort_column, sort_type = model.get_sort_column_id()
        date1 = model.get_value(row1, sort_column) \
            or datetime.date(datetime.MINYEAR, 1, 1)
        date2 = model.get_value(row2, sort_column) \
            or datetime.date(datetime.MINYEAR, 1, 1)
        epoch1 = time.mktime(date1.timetuple())
        epoch2 = time.mktime(date2.timetuple())
        return cmp(epoch1, epoch2)
