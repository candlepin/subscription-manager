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

import datetime
import gettext
import time

from subscription_manager import ga
from subscription_manager.gui import widgets
from subscription_manager.gui.storage import MappedListStore
from subscription_manager import isodate
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.managerlib import allows_multi_entitlement

_ = gettext.gettext


class ContractSelectionWindow(widgets.SubmanBaseWidget):
    widget_names = ["contract_selection_window", "subscribe_button",
                    "edit_quantity_label", "contract_selection_treeview",
                    "subscription_name_label", "total_contracts_label"]
    gui_file = "contract_selection.glade"

    def __init__(self, selected_callback, cancel_callback):
        super(ContractSelectionWindow, self).__init__()
        self._selected_callback = selected_callback
        self._cancel_callback = cancel_callback
        self.total_contracts = 0

        self.contract_selection_treeview.get_selection().connect("changed",
            self._on_contract_selection)

        self.subscription_name_label.set_line_wrap(True)

        callbacks = {"on_cancel_button_clicked": self._cancel_button_clicked,
                     "size-allocate": lambda label, size: label.set_size_request(size.width - 1, -1),
                     "on_subscribe_button_clicked": self._subscribe_button_clicked}
        self.connect_signals(callbacks)

        self.model = MappedListStore(self.get_type_map())
        self.contract_selection_treeview.set_model(self.model)

    def get_type_map(self):
        return {
                'contract_number': str,
                'consumed_fraction': str,
                'start_date': ga.GObject.TYPE_PYOBJECT,
                'end_date': ga.GObject.TYPE_PYOBJECT,
                'default_quantity': int,
                'product_name': str,
                'pool': ga.GObject.TYPE_PYOBJECT,
                'is_virt_only': bool,
                'multi_entitlement': bool,
                'quantity_available': int,
                'quantity_increment': int,
                }

    def show(self):
        self.populate_treeview()
        self.contract_selection_window.show_all()

    def destroy(self):
        self.contract_selection_window.destroy()

    def populate_treeview(self):
        renderer = ga.Gtk.CellRendererText()
        column = ga.Gtk.TreeViewColumn(_("Contract"),
                                       renderer,
                                       text=self.model['contract_number'])
        column.set_expand(True)
        column.set_sort_column_id(self.model['contract_number'])
        self.model.set_sort_func(self.model['contract_number'],
                                 self._sort_text, None)
        self.contract_selection_treeview.append_column(column)

        column = widgets.MachineTypeColumn(self.model['is_virt_only'])
        column.set_sort_column_id(self.model['is_virt_only'])
        self.model.set_sort_func(self.model['is_virt_only'],
                                 self._sort_machine_type, column)
        self.contract_selection_treeview.append_column(column)

        renderer = ga.Gtk.CellRendererText()
        renderer.set_property("xalign", 0.5)
        column = ga.Gtk.TreeViewColumn(_("Used / Total"),
                                    renderer,
                                    text=self.model['consumed_fraction'])
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = ga.Gtk.TreeViewColumn(_("Start Date"),
                                    renderer,
                                    date=self.model['start_date'])
        column.set_sort_column_id(self.model['start_date'])
        self.model.set_sort_func(self.model['start_date'],
                                 self._sort_date, None)
        self.contract_selection_treeview.append_column(column)

        renderer = widgets.CellRendererDate()
        column = ga.Gtk.TreeViewColumn(_("End Date"),
                                    renderer,
                                    date=self.model['end_date'])
        column.set_sort_column_id(self.model['end_date'])
        self.model.set_sort_func(self.model['end_date'],
                                 self._sort_date,
                                 None)
        self.contract_selection_treeview.append_column(column)

        column = widgets.QuantitySelectionColumn(_("Quantity"), self.model,
                self.model['default_quantity'],
                self.model['multi_entitlement'],
                self.model['quantity_available'],
                self.model['quantity_increment'])
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
        # for that pool. See #855257. Watch out for quantity_available
        # being -1 (unlimited).
        if default_quantity_value > quantity_available and quantity_available >= 0:
            default_quantity_value = quantity_available

        quantity_increment = 1
        if 'calculatedAttributes' in pool:
            calculated_attrs = pool['calculatedAttributes']

            if 'quantity_increment' in calculated_attrs:
                quantity_increment = int(calculated_attrs['quantity_increment'])

        self.model.add_map({
            'contract_number': pool['contractNumber'],
            'consumed_fraction': "%s / %s" % (pool['consumed'], quantity),
            'start_date': isodate.parse_date(pool['startDate']),
            'end_date': isodate.parse_date(pool['endDate']),
            'default_quantity': default_quantity_value,
            'product_name': pool['productName'],
            'pool': pool,
            'is_virt_only': PoolWrapper(pool).is_virt_only(),
            'multi_entitlement': allows_multi_entitlement(pool),
            'quantity_available': quantity_available,
            'quantity_increment': quantity_increment,
            })

    def toplevel(self):
        tl = self.get_toplevel()
        if tl.is_toplevel():
            return tl
        else:
            self.log.debug("no toplevel window?")
            return None

    def set_parent_window(self, window):
        self.log.debug('window %s', window)
        self.contract_selection_window.set_transient_for(window)

    def _cancel_button_clicked(self, button):
        self._cancel_callback()

    def _subscribe_button_clicked(self, button):
        selection = self.contract_selection_treeview.get_selection()
        model, iter = selection.get_selected()
        if iter is not None:
            pool, quantity = model.get(iter, model['pool'],
                                       model['default_quantity'])
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
        for row in [row1, row2]:
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
