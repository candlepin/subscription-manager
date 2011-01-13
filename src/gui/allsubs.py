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
import os
import logging
import gtk
import gobject
import progress
import gettext
_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)
import managergui
import managerlib

import widgets
import storage
import async
from utils import handle_gui_exception
from contract_selection import ContractSelectionWindow

class AllSubscriptionsTab(widgets.SubscriptionManagerTab):

    def __init__(self, backend, consumer, facts):
        widget_names = ['details_box', 'date_picker_hbox',
                        'compatible_checkbutton', 'overlap_checkbutton',
                        'not_installed_checkbutton', 'contains_text_entry',
                        'month_entry', 'day_entry', 'year_entry',
                        'active_on_checkbutton', 'subscribe_button']
        super(AllSubscriptionsTab, self).__init__('allsubs.glade', widget_names)

        self.backend = backend
        self.consumer = consumer
        self.facts = facts

        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        today = datetime.date.today()
        self.date_picker = widgets.DatePicker(today)
        self.date_picker_hbox.add(self.date_picker)

        self.add_text_column(_('Subscription'), 'product_name', True)
        self.add_text_column(_('Available Subscriptions'), 'available')

        # This option should be selected by default:
        self.compatible_checkbutton.set_active(True)
        self.sub_details = widgets.SubDetailsWidget(show_contract=False)
        self.details_box.add(self.sub_details.get_widget())

        self.contract_selection = None

        self.glade.signal_autoconnect({
            "on_search_button_clicked": self.search_button_clicked,
            "on_compatible_checkbutton_clicked": self.filters_changed,
            "on_overlap_checkbutton_clicked": self.filters_changed,
            "on_not_installed_checkbutton_clicked": self.filters_changed,
            "on_contain_text_entry_changed": self.contain_text_entry_changed,
            "on_subscribe_button_clicked": self.subscribe_button_clicked,
        })

    def get_type_map(self):
        return {
            'product_name': str,
            'available': str,
            'product_id': str,
            'pool_id': str,
            'merged_pools': gobject.TYPE_PYOBJECT,

            # TODO:  This is not needed here - i think maybe we should get
            #        rid of the background color stuff altogether...
            'background': str,
            'align': float,
        }

    def show_compatible(self):
        """ Return True if we're to include pools which failed a rule check. """
        return self.compatible_checkbutton.get_active()

    def show_overlapping(self):
        """
        Return True if we're to include pools which provide products for
        which we already have subscriptions.
        """
        return self.overlap_checkbutton.get_active()

    def show_uninstalled(self):
        """
        Return True if we're to include pools for products that are
        not installed.
        """
        return self.not_installed_checkbutton.get_active()

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
        self.store.clear()

        merged_pools = self.pool_stash.merge_pools(
                compatible=self.show_compatible(),
                overlapping=self.show_overlapping(),
                uninstalled=self.show_uninstalled(),
                text=self.get_filter_text())

        for entry in merged_pools.values():
            self.store.add_map({
                'product_name': entry.product_name,
                'available': entry.quantity - entry.consumed,
                'product_id': entry.product_id,
                'pool_id': entry.pools[0]['id'], # not displayed, just for lookup later
                'merged_pools': entry, # likewise not displayed, for subscription
                'align': 0.5
        })

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
            handle_gui_exception(e, _("Error fetching subscriptions from server"))

    def _update_display(self, error=None):
        if self.pb:
            self.pb.hide()
            gobject.source_remove(self.timer)
            self.timer = 0
            self.pb = None

        if error:
            handle_gui_exception(error,
                    _("Unable to search for subscriptions"))
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

    def _contract_selected(self, pool):
        self._contract_selection_cancelled()
        try:
            self.backend.uep.bindByEntitlementPool(self.consumer.uuid, pool['id'])
            managergui.fetch_certificates(self.backend)
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

        # Decide if we need to show the contract selection dialog or not.
        # if there's just one pool, shortcut right to the callback that the
        # dialog would have run.
        if len(pools.pools) == 1:
            self._contract_selected(pools.pools[0])
            return

        self.contract_selection = ContractSelectionWindow(
                self._contract_selected, self._contract_selection_cancelled)

        self.contract_selection.set_parent_window(self.content.get_parent_window().get_user_data())

        for pool in pools.pools:
            self.contract_selection.add_pool(pool)

        self.contract_selection.show()

    def on_selection(self, selection):
        """ Shows details for the current selected pool. """
        if selection.is_valid():
            product_name = selection['product_name']
            pool_id = selection['pool_id']
            provided = self.pool_stash.lookup_provided_products(pool_id)
            self.sub_details.show(product_name, products=provided)
        else:
            self.sub_details.clear()

        self.subscribe_button.set_sensitive(selection.is_valid())

