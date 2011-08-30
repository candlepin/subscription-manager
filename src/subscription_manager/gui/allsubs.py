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
import logging
import gobject

import gettext
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.gui.widgets import MachineTypeColumn, MultiEntitlementColumn, \
                                             QuantitySelectionColumn
from subscription_manager.jsonwrapper import PoolWrapper
import gtk
from subscription_manager.managerlib import MergedPoolsStackingGroupSorter
_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)
from subscription_manager import managerlib

from subscription_manager.gui import widgets
from subscription_manager import async
from subscription_manager.gui import progress
from subscription_manager.gui.utils import handle_gui_exception, apply_highlight, errorWindow,\
    get_cell_background_color, set_background_model_index
from subscription_manager.gui.contract_selection import ContractSelectionWindow
from subscription_manager.quantity import QuantityDefaultValueCalculator, valid_quantity, \
                                          allows_multi_entitlement
from subscription_manager.gui.storage import MappedTreeStore


class AllSubscriptionsTab(widgets.SubscriptionManagerTab):

    def __init__(self, backend, consumer, facts):
        widget_names = ['details_box', 'date_picker_hbox',
                        'compatible_checkbutton', 'overlap_checkbutton',
                        'installed_checkbutton', 'contains_text_entry',
                        'month_entry', 'day_entry', 'year_entry',
                        'active_on_checkbutton', 'subscribe_button',
                        'edit_quantity_label']
        super(AllSubscriptionsTab, self).__init__('allsubs.glade', widget_names)

        self.backend = backend
        self.consumer = consumer
        self.facts = facts

        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        today = datetime.date.today()
        self.date_picker = widgets.DatePicker(today)
        self.date_picker_hbox.add(self.date_picker)

        # Custom build of the subscription column.
        title_text_renderer = gtk.CellRendererText()
        title_text_renderer.set_property('xalign', 0.0)
        subscription_column = gtk.TreeViewColumn(_('Subscription'),
                                        title_text_renderer,
                                        markup=self.store['product_name_formatted'])
        subscription_column.set_expand(True)
        self.top_view.append_column(subscription_column)

        machine_type_col = MachineTypeColumn(self.store['virt_only'])
        self.top_view.append_column(machine_type_col)

        multi_entitle_col = MultiEntitlementColumn(self.store['multi-entitlement'])
        self.top_view.append_column(multi_entitle_col)

        # Set up the quantity column.
        quantity_column = QuantitySelectionColumn(_("Quantity"),
                                                  self.store['quantity_to_consume'],
                                                  self.store['multi-entitlement'])
        self.top_view.append_column(quantity_column)

        self.edit_quantity_label.set_label(quantity_column.get_column_legend_text())

        self.add_text_column(_('Available Subscriptions'), 'available')

        # Ensure all cells are colored according the the store.
        set_background_model_index(self.top_view, self.store['background'])

        self.top_view.connect("row_activated",
                              widgets.expand_collapse_on_row_activated_callback)

        # This option should be selected by default:
        self.compatible_checkbutton.set_active(True)
        self.sub_details = widgets.SubDetailsWidget(show_contract=False)
        self.details_box.add(self.sub_details.get_widget())

        self.contract_selection = None

        self.glade.signal_autoconnect({
            "on_search_button_clicked": self.search_button_clicked,
            "on_compatible_checkbutton_clicked": self.filters_changed,
            "on_overlap_checkbutton_clicked": self.filters_changed,
            "on_installed_checkbutton_clicked": self.filters_changed,
            "on_contain_text_entry_changed": self.contain_text_entry_changed,
            "on_subscribe_button_clicked": self.subscribe_button_clicked,
        })

    # Override so that we can use a tree store.
    def get_store(self):
        return MappedTreeStore(self.get_type_map())

    def _setup_title_text_renderer(self, column, markup, text_model_idx):
        title_text_renderer = gtk.CellRendererText()
        title_text_renderer.set_property('xalign', 0.0)
        self.pack_start(title_text_renderer, True)

        renderer_attr = "text"
        if markup:
            renderer_attr = "markup"
        self.add_attribute(title_text_renderer, renderer_attr, text_model_idx)
        return title_text_renderer

    def get_type_map(self):
        return {
            'virt_only': bool,
            'product_name': str,
            'available': str,
            'product_id': str,
            'pool_id': str,
            'merged_pools': gobject.TYPE_PYOBJECT,
            'product_name_formatted': str,
            'quantity_to_consume': int,
            'background': str,

            # TODO:  This is not needed here.
            'align': float,
            'multi-entitlement': bool,
        }

    def filter_incompatible(self):
        """
        Return True if we're not to include pools which failed a rule check.
        """
        return self.compatible_checkbutton.get_active()

    def filter_overlapping(self):
        """
        Return True if we're not to include pools which provide products for
        which we already have subscriptions.
        """
        return self.overlap_checkbutton.get_active()

    def filter_uninstalled(self):
        """
        Return True if we're not to include pools for products that are
        not installed.
        """
        return self.installed_checkbutton.get_active()

    def get_filter_text(self):
        """
        Returns the text to filter subscriptions based on. Will return None
        if the text box is empty.
        """
        contains_text = self.contains_text_entry.get_text()
        if not contains_text:
            contains_text = None

        return contains_text

    def clear_pools(self):
        """
        Clear pools list.
        """
        self.store.clear()

    def display_pools(self):
        """
        Re-display the list of pools last queried, based on current filter options.
        """
        selection = self.top_view.get_selection()
        selected_pool_id = None
        itr = selection.get_selected()[1]
        if itr:
            selected_pool_id = self.store.get_value(itr, self.store['pool_id'])

        self.store.clear()

        quantity_defaults_calculator = QuantityDefaultValueCalculator(self.facts,
                                                            EntitlementDirectory().list())

        merged_pools = self.pool_stash.merge_pools(
                incompatible=self.filter_incompatible(),
                overlapping=self.filter_overlapping(),
                uninstalled=self.filter_uninstalled(),
                subscribed=True,
                text=self.get_filter_text())
        sorter = MergedPoolsStackingGroupSorter(merged_pools.values())
        for group_idx, group in enumerate(sorter.groups):
            bg_color = get_cell_background_color(group_idx)
            iter = None
            if group.name:
                iter = self.store.add_map(iter, self._create_parent_map(group.name, bg_color))

            for entry in group.entitlements:
                if entry.quantity < 0:
                    available = _('unlimited')
                else:
                    available = entry.quantity - entry.consumed

                pool = entry.pools[0]
                self.store.add_map(iter, {
                    'virt_only': PoolWrapper(entry.pools[0]).is_virt_only(),
                    'product_name': entry.product_name,
                    'product_name_formatted': \
                            apply_highlight(entry.product_name,
                                self.get_filter_text()),
                    'quantity_to_consume': \
                        quantity_defaults_calculator.calculate(pool),
                    'available': available,
                    'product_id': entry.product_id,
                    'pool_id': entry.pools[0]['id'],  # not displayed, just for lookup later
                    'merged_pools': entry,  # likewise not displayed, for subscription
                    'align': 0.5,
                    'multi-entitlement': allows_multi_entitlement(pool),
                    'background': bg_color,
                })

        # Ensure that all nodes are expanded in the tree view.
        self.top_view.expand_all()

        # set the selection/details back to what they were, if possible
        found = False
        if selected_pool_id:
            itr = self.store.get_iter_first()
            while itr != None:
                if self.store.get_value(itr,
                        self.store['pool_id']) == selected_pool_id:
                    self.top_view.set_cursor(self.store.get_path(itr))
                    found = True
                    break
                else:
                    itr = self.store.iter_next(itr)
        if not found:
            self.sub_details.clear()

    def _create_parent_map(self, title, bg_color):
        return {
                    'virt_only': False,
                    'product_name': title,
                    'product_name_formatted': \
                            apply_highlight(title,
                                self.get_filter_text()),
                    'quantity_to_consume': 0,
                    'available': "",
                    'product_id': "",
                    'pool_id':"",  # not displayed, just for lookup later
                    'merged_pools': None,  # likewise not displayed, for subscription
                    'align': 0.5,
                    'multi-entitlement': False,
                    'background': bg_color,
                }

    def get_label(self):
        return _("All Available Subscriptions")

    def search_button_clicked(self, widget):
        """
        Reload the subscriptions from the server when the Search button
        is clicked.
        """
        try:
            async_stash = async.AsyncPool(self.pool_stash)
            async_stash.refresh(self.date_picker.date, self._update_display)
            # show pulsating progress bar while we wait for results
            self.pb = progress.Progress(
                    _("Searching for subscriptions. Please wait."))
            self.timer = gobject.timeout_add(100, self.pb.pulse)
            self.pb.set_parent_window(self.content.get_parent_window().get_user_data())
        except Exception, e:
            handle_gui_exception(e, _("Error fetching subscriptions from server:  %s"))

    def _update_display(self, data, error):
        if self.pb:
            self.pb.hide()
            gobject.source_remove(self.timer)
            self.timer = 0
            self.pb = None

        if error:
            handle_gui_exception(error, _("Unable to search for subscriptions:  %s"))
        else:
            self.display_pools()

    def contain_text_entry_changed(self, widget):
        """
        Redisplay the pools based on the new search string.
        """
        self.display_pools()

    def filters_changed(self, widget):
        """
        Callback used by several widgets related to filtering, anytime
        something changes, we re-display based on the latest choices.
        """
        log.debug("filters changed")
        self.display_pools()

    def _contract_selected(self, pool, quantity=1):
        if not valid_quantity(quantity):
            errorWindow(_("Quantity must be a positive number."))
            return

        self._contract_selection_cancelled()
        try:
            self.backend.uep.bindByEntitlementPool(self.consumer.uuid, pool['id'], quantity)
            managerlib.fetch_certificates(self.backend)

        except Exception, e:
            handle_gui_exception(e, _("Error getting subscription: %s"))

        #Force the search results to refresh with the new info
        self.search_button_clicked(None)

    def _contract_selection_cancelled(self):
        if self.contract_selection:
            self.contract_selection.destroy()
        self.contract_selection = None

    def subscribe_button_clicked(self, button):
        model, tree_iter = self.top_view.get_selection().get_selected()
        pools = model.get_value(tree_iter, self.store['merged_pools'])
        quantity_to_consume = model.get_value(tree_iter, self.store['quantity_to_consume'])

        # Decide if we need to show the contract selection dialog or not.
        # If there's just one pool and does not allow multi-entitlement,
        # shortcut right to the callback that the dialog would have run.
        if len(pools.pools) == 1:
            self._contract_selected(pools.pools[0], quantity_to_consume)
            return

        self.contract_selection = ContractSelectionWindow(
                self._contract_selected, self._contract_selection_cancelled)

        self.contract_selection.set_parent_window(self.content.get_parent_window().get_user_data())

        for pool in pools.pools:
            self.contract_selection.add_pool(pool, quantity_to_consume)

        self.contract_selection.show()

    def _selection_callback(self, treeselection):
        model, tree_iter = treeselection.get_selected()
        if model.iter_n_children(tree_iter) > 0:
            self.sub_details.clear()
            self.on_no_selection()
        else:
            widgets.SubscriptionManagerTab._selection_callback(self, treeselection)

    def on_selection(self, selection):
        """ Shows details for the current selected pool. """
        if selection.is_valid():
            product_name = selection['product_name']
            pool_id = selection['pool_id']
            provided = self.pool_stash.lookup_provided_products(pool_id)
            self.sub_details.show(product_name, products=provided, highlight=self.get_filter_text())
        else:
            self.sub_details.clear()

        self.subscribe_button.set_sensitive(selection.is_valid())

    def on_no_selection(self):
        self.subscribe_button.set_sensitive(False)
