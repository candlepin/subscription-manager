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
import gobject
import logging

import gtk

from subscription_manager import async
from subscription_manager.gui.contract_selection import ContractSelectionWindow
from subscription_manager.gui.filter import FilterOptionsWindow, Filters
from subscription_manager.gui import progress
from subscription_manager.gui.storage import MappedTreeStore
from subscription_manager.gui.utils import apply_highlight, show_error_window, handle_gui_exception, set_background_model_index
from subscription_manager.gui import widgets
from subscription_manager.injection import IDENTITY, require
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager import managerlib
from subscription_manager.managerlib import allows_multi_entitlement, valid_quantity

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class AllSubscriptionsTab(widgets.SubscriptionManagerTab):
    widget_names = widgets.SubscriptionManagerTab.widget_names + \
                       ['details_box', 'date_picker_hbox',
                        'month_entry', 'day_entry', 'year_entry',
                        'active_on_checkbutton', 'subscribe_button',
                        'edit_quantity_label', 'scrolledwindow',
                        'filter_options_button', 'applied_filters_label']
    gui_file = "allsubs.glade"

    def __init__(self, backend, facts, parent_win):

        super(AllSubscriptionsTab, self).__init__()

        # Set up dynamic elements
        self.no_subs_label, self.no_subs_label_viewport = widgets.get_scrollable_label()
        # Add at-spi because we no longer create this widget from glade
        self.top_view.get_accessible().set_name(_("All Subscriptions View"))
        self.widget_switcher = widgets.WidgetSwitcher(self.scrolledwindow,
                self.no_subs_label_viewport, self.top_view)
        self.widget_switcher.set_active(0)

        self.parent_win = parent_win
        self.backend = backend
        self.identity = require(IDENTITY)
        self.facts = facts

        # Progress bar
        self.pb = None
        self.timer = 0

        self.pool_stash = managerlib.PoolStash(self.facts)

        self.async_bind = async.AsyncBind(self.backend.certlib)

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
        cols = []
        cols.append((subscription_column, 'text', 'product_name_formatted'))

        machine_type_col = widgets.MachineTypeColumn(self.store['virt_only'])
        self.top_view.append_column(machine_type_col)
        cols.append((machine_type_col, 'text', 'virt_only'))

        column = self.add_text_column(_('Available'), 'available')
        cols.append((column, 'text', 'available'))

        # Set up the quantity column.
        quantity_column = widgets.QuantitySelectionColumn(_("Quantity"),
                                                          self.store,
                                                          self.store['quantity_to_consume'],
                                                          self.store['multi-entitlement'],
                                                          self.store['quantity_available'],
                                                          self.store['quantity_increment'])
        self.top_view.append_column(quantity_column)

        self.set_sorts(self.store, cols)

        self.edit_quantity_label.set_label(quantity_column.get_column_legend_text())



        # FIXME: Likely a correct way to do this now, so stub this out now
        # Ensure all cells are colored according the the store.
        #set_background_model_index(self.top_view, self.store['background'])
        # FIXME


        self.top_view.connect("row_activated",
                              widgets.expand_collapse_on_row_activated_callback)

        # This option should be selected by default:
        self.sub_details = widgets.SubDetailsWidget(backend.product_dir)
        self.details_box.add(self.sub_details.get_widget())

        self.contract_selection = None

        self.filters = Filters(show_compatible=True, show_no_overlapping=True)
        self.filter_dialog = FilterOptionsWindow(self.filters, self)

        self.update_applied_filters_label()
        self.connect_signals({
            "on_search_button_clicked": self.search_button_clicked,
            "on_subscribe_button_clicked": self.subscribe_button_clicked,
            "on_filter_options_button_clicked": self.filter_options_button_clicked,
        })

        # Nothing displayed initially:
        self.clear_pools()

    # Override so that we can use a tree store.
    def get_store(self):
        return MappedTreeStore(self.get_type_map())

    def get_type_map(self):
        return {
            'virt_only': gobject.TYPE_PYOBJECT,
            'product_name': str,
            'available': str,
            'product_id': str,
            'pool_id': str,
            'merged_pools': gobject.TYPE_PYOBJECT,
            'product_name_formatted': str,
            'quantity_to_consume': int,
            'background': str,
            'support_type': str,
            'support_level': str,

            # TODO:  This is not needed here.
            'align': float,
            'multi-entitlement': bool,
            'quantity_available': int,
            'quantity_increment': int,
            'pool_type': str
        }

    def get_filter_text(self):
        """
        Returns the text to filter subscriptions based on. Will return None
        if the text box is empty.
        """
        contains_text = self.filters.contains_text
        if not contains_text:
            contains_text = None

        return contains_text

    def clear_pools(self):
        """
        Clear pools list.
        """
        self.store.clear()
        self.display_message(_("Press Update to search for subscriptions."))

    def display_message(self, message):
        """
        Show a message in situations where we have no subscriptions to show.
        """
        self.no_subs_label.set_markup("<b><big>%s</big></b>" % message)
        self.widget_switcher.set_active(0)

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

        # It may seem backwards that incompatible = self.filters.show_compatible
        # etc., but think of it like "if show_compatible is true, then
        # filter out all the incompatible products."
        merged_pools = self.pool_stash.merge_pools(
                incompatible=self.filters.show_compatible,
                overlapping=self.filters.show_no_overlapping,
                uninstalled=self.filters.show_installed,
                subscribed=True,
                text=self.get_filter_text())

        if self.pool_stash.all_pools_size() == 0:
            self.sub_details.clear()
            # If the date is None (now), use current time
            on_date = self.date_picker.date or datetime.datetime.now()
            self.display_message(_("No subscriptions are available on %s.") %
                                   on_date.strftime("%Y-%m-%d"))
            return

        if len(merged_pools) == 0:
            self.sub_details.clear()
            self.display_message(_("No subscriptions match current filters."))
            return

        # Hide the no subscriptions label and show the pools list:
        self.widget_switcher.set_active(1)

        sorter = managerlib.MergedPoolsStackingGroupSorter(merged_pools.values())
        for group in sorter.groups:
            tree_iter = None
            if group.name and len(group.entitlements) > 1:
                tree_iter = self.store.add_map(tree_iter, self._create_parent_map(group.name))

            for entry in group.entitlements:
                quantity_available = 0
                if entry.quantity < 0:
                    available = _('Unlimited')
                    quantity_available = -1
                else:
                    available = entry.quantity - entry.consumed
                    quantity_available = entry.quantity - entry.consumed

                pool = entry.pools[0]
                # Use the maximum suggested quantity, not the first one.  BZ 1022198
                # This is still incorrect when quantities from multiple merged pools are required
                suggested_quantity = max(map(lambda p: self.calculate_default_quantity(p), entry.pools))

                pool_type = PoolWrapper(pool).get_pool_type()

                attrs = self._product_attrs_to_dict(pool['productAttributes'])

                # Display support level and type if the attributes are present:
                support_level = ""
                support_type = ""
                if 'support_level' in attrs:
                    support_level = attrs['support_level']
                if 'support_type' in attrs:
                    support_type = attrs['support_type']

                quantity_increment = 1
                if 'calculatedAttributes' in pool:
                    calculated_attrs = pool['calculatedAttributes']

                    if 'quantity_increment' in calculated_attrs:
                        quantity_increment = int(calculated_attrs['quantity_increment'])

                self.store.add_map(tree_iter, {
                    'virt_only': self._machine_type(entry.pools),
                    'product_name': str(entry.product_name),
                    'product_name_formatted': apply_highlight(entry.product_name,
                                                              self.get_filter_text()),
                    'quantity_to_consume': suggested_quantity,
                    'available': str(available),
                    'product_id': str(entry.product_id),
                    'pool_id': entry.pools[0]['id'],  # not displayed, just for lookup later
                    'merged_pools': entry,  # likewise not displayed, for subscription
                    'align': 0.5,
                    'multi-entitlement': allows_multi_entitlement(pool),
                    'background': None,
                    'quantity_available': quantity_available,
                    'support_level': support_level,
                    'support_type': support_type,
                    'quantity_increment': quantity_increment,
                    'pool_type': str(pool_type)
                })

        # Ensure that all nodes are expanded in the tree view.
        self.top_view.expand_all()
        self._stripe_rows(None, self.store)

        # set the selection/details back to what they were, if possible
        def select_row(model, path, itr, data):
            if model.get_value(itr, model['pool_id']) == data[0]:
                data[1].set_cursor(path)
                return True

        # Attempt to re-select if there was a selection
        if selected_pool_id:
            self.store.foreach(select_row, (selected_pool_id, self.top_view))

        # If we don't have a selection, clear the sub_details view
        # TODO: is this conditional necessary?  If so, when?
        if not self.top_view.get_selection().get_selected()[1]:
            self.sub_details.clear()

    def _product_attrs_to_dict(self, product_attributes_list):
        """
        Convert the JSON list of product attributes into a dict we can
        work with more easily.
        """
        return dict((pa['name'], pa['value']) for pa in product_attributes_list)

    # need to determine what type of machine the product is for
    #  based on the pools accumulated.
    # returns true for virtual, false for physical, and
    #  None for both.
    def _machine_type(self, pools):
        virt_only = None
        first = True
        for pool in pools:
            if first:
                virt_only = PoolWrapper(pool).is_virt_only()
                first = False
            else:
                if virt_only != PoolWrapper(pool).is_virt_only():
                    return None
        return virt_only

    def _create_parent_map(self, title):
        return {
                    'virt_only': False,
                    'product_name': title,
                    'product_name_formatted': apply_highlight(title, self.get_filter_text()),
                    'quantity_to_consume': 0,
                    'available': "",
                    'product_id': "",
                    'pool_id': "",  # not displayed, just for lookup later
                    'merged_pools': None,  # likewise not displayed, for subscription
                    'align': 0.5,
                    'multi-entitlement': False,
                    'background': None,
                    'quantity_available': 0,
                    'support_level': "",
                    'support_type': "",
                    'quantity_increment': 1,
                    'pool_type': ''
                }

    def get_label(self):
        return _("All Available Subscriptions")

    def search_button_clicked(self, widget=None):
        """
        Reload the subscriptions from the server when the Search button
        is clicked.
        """
        if not self.date_picker.date_entry_validate():
            return
        try:
            pb_title = _("Searching")
            pb_label = _("Searching for subscriptions. Please wait.")
            if self.pb:
                self.pb.set_title(pb_title)
                self.pb.set_label(pb_label)
            else:
                # show pulsating progress bar while we wait for results
                self.pb = progress.Progress(pb_title, pb_label)
                self.timer = gobject.timeout_add(100, self.pb.pulse)
                #self.pb.set_parent_window(self.content.get_parent_window().get_user_data())

            # fire off async refresh
            async_stash = async.AsyncPool(self.pool_stash)
            async_stash.refresh(self.date_picker.date, self._update_display)
        except Exception, e:
            handle_gui_exception(e, _("Error fetching subscriptions from server:  %s"),
                    self.parent_win)

    def _clear_progress_bar(self):
        if self.pb:
            self.pb.hide()
            gobject.source_remove(self.timer)
            self.timer = 0
            self.pb = None

    def _update_display(self, data, error):
        self._clear_progress_bar()

        if error:
            handle_gui_exception(error, _("Unable to search for subscriptions:  %s"),
                    self.parent_win)
        else:
            self.display_pools()

    # Called after the bind, but before certlib update
    def _async_bind_callback(self):
        self.search_button_clicked()

    def _async_bind_exception_callback(self, e):
        self._clear_progress_bar()
        handle_gui_exception(e, _("Error getting subscription: %s"), self.parent_win)

    def _contract_selected(self, pool, quantity=1):
        if not valid_quantity(quantity):
            show_error_window(_("Quantity must be a positive number."),
                              parent=self.parent_win)
            return

        self._contract_selection_cancelled()

        # Start the progress bar
        self.pb = progress.Progress(_("Attaching"),
                _("Attaching subscription. Please wait."))
        self.timer = gobject.timeout_add(100, self.pb.pulse)
        #self.pb.set_parent_window(self.content.get_parent_window().get_user_data())

        # Spin off a thread to handle binding the selected pool.
        # After it has completed the actual bind call, available
        # subs will be refreshed, but we won't re-run compliance
        # until we have serialized the certificates
        self.async_bind.bind(pool, quantity,
                bind_callback=self._async_bind_callback,
                cert_callback=self.backend.cs.force_cert_check,
                except_callback=self._async_bind_exception_callback)

    def _contract_selection_cancelled(self):
        if self.contract_selection:
            self.contract_selection.destroy()
        self.contract_selection = None

    def update_applied_filters_label(self):
        self.applied_filters_label.set_text(_("%s applied") %
                                              self.filters.get_applied_count())

    def filter_options_button_clicked(self, button):
        self.filter_dialog.show()

    def subscribe_button_clicked(self, button):
        model, tree_iter = self.top_view.get_selection().get_selected()
        merged_pools = model.get_value(tree_iter, self.store['merged_pools'])
        quantity_to_consume = model.get_value(tree_iter, self.store['quantity_to_consume'])

        # Decide if we need to show the contract selection dialog or not.
        # If there's just one pool and does not allow multi-entitlement,
        # shortcut right to the callback that the dialog would have run.
        if len(merged_pools.pools) == 1:
            self._contract_selected(merged_pools.pools[0], quantity_to_consume)
            return

        self.contract_selection = ContractSelectionWindow(
                self._contract_selected, self._contract_selection_cancelled)

        self.contract_selection.set_parent_window(self.content.get_parent_window().get_user_data())
        merged_pools.sort_virt_to_top()

        for pool in merged_pools.pools:
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
            support_level = selection['support_level']
            support_type = selection['support_type']
            provided = self.pool_stash.lookup_provided_products(pool_id)

            self.sub_details.show(product_name, products=provided,
                    highlight=self.get_filter_text(),
                    support_level=support_level, support_type=support_type,
                    sku=selection['product_id'],
                    pool_type=selection['pool_type'])
        else:
            self.sub_details.clear()

        self.subscribe_button.set_sensitive(selection.is_valid())

    def on_no_selection(self):
        self.subscribe_button.set_sensitive(False)

    def calculate_default_quantity(self, pool):

        try:
            return int(pool['calculatedAttributes']['suggested_quantity'])
        except:
            return 1
