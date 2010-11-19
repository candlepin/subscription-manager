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
import gtk
import gobject
import logging
import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)
import managerlib
import managergui

from facts import Facts
from widgets import SubDetailsWidget
from dateselect import DateSelector
from utils import handle_gui_exception
from contract_selection import ContractSelectionWindow

prefix = os.path.dirname(__file__)
ALL_SUBS_GLADE = os.path.join(prefix, "data/allsubs.glade")

# Pointers into the data store we're displaying:
PRODUCT_NAME_INDEX = 0
BUNDLED_COUNT_INDEX = 1
POOL_COUNT_INDEX = 2
QUANTITY_INDEX = 3
AVAIL_INDEX = 4
PRODUCT_ID_INDEX = 5
POOL_ID_INDEX = 6
MERGED_POOLS_INDEX = 7


class AllSubscriptionsTab(object):

    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer
        self.facts = facts

        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        self.all_subs_xml = gtk.glade.XML(ALL_SUBS_GLADE)
        self.all_subs_vbox = self.all_subs_xml.get_widget('all_subs_vbox')
        self.all_subs_vbox.unparent()

        today = datetime.date.today()
        self.date_selector = DateSelector(self.active_on_date_changed, initial_date=today)

        self.subs_store = gtk.ListStore(str, str, str, str, str, str, str,
                gobject.TYPE_PYOBJECT)
        self.subs_treeview = self.all_subs_xml.get_widget('all_subs_treeview')
        self.subs_treeview.set_model(self.subs_store)
        self._add_column(_("Subscription"), PRODUCT_NAME_INDEX)
        self._add_column(_("# Bundled Products"), BUNDLED_COUNT_INDEX)
        self._add_column(_("Total Contracts"), POOL_COUNT_INDEX)
        self._add_column(_("Total Subscriptions"), QUANTITY_INDEX)
        self._add_column(_("Available Subscriptions"), AVAIL_INDEX)

        self.compatible_checkbutton = self.all_subs_xml.get_widget(
                'compatible_checkbutton')
        # This option should be selected by default:
        self.compatible_checkbutton.set_active(True)
        self.overlap_checkbutton = self.all_subs_xml.get_widget(
                'overlap_checkbutton')
        self.not_installed_checkbutton = self.all_subs_xml.get_widget(
                'not_installed_checkbutton')
        self.contains_text_checkbutton = self.all_subs_xml.get_widget(
                'contains_text_checkbutton')
        self.contains_text_entry = self.all_subs_xml.get_widget(
                'contain_text_entry')
        self.month_entry = self.all_subs_xml.get_widget("month_entry")
        self.day_entry = self.all_subs_xml.get_widget("day_entry")
        self.year_entry = self.all_subs_xml.get_widget("year_entry")
        self.sub_details = SubDetailsWidget(show_contract=False)
        self.all_subs_vbox.pack_start(self.sub_details.get_widget())

        self.active_on_checkbutton = self.all_subs_xml.get_widget('active_on_checkbutton')

        # Set the date filter to todays date by default:
        self._set_active_on_text(today.year, today.month, today.day)

        self.subscribe_button = self.all_subs_xml.get_widget('subscribe_button')

        self.all_subs_xml.signal_autoconnect({
            "on_search_button_clicked": self.search_button_clicked,
            "on_date_select_button_clicked": self.date_select_button_clicked,
            "on_compatible_checkbutton_clicked": self.filters_changed,
            "on_overlap_checkbutton_clicked": self.filters_changed,
            "on_not_installed_checkbutton_clicked": self.filters_changed,
            "on_contains_text_checkbutton_clicked": self.filters_changed,
            "on_contain_text_entry_changed": self.filters_changed,
            "on_subscribe_button_clicked": self.subscribe_button_clicked,
        })
        self.subs_treeview.get_selection().connect('changed', self.update_sub_details)


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
        if the text box is empty, or the filter checkbox is not enabled.
        """
        if self.contains_text_checkbutton.get_active():
            contains_text = self.contains_text_entry.get_text()
            if contains_text != "":
                return contains_text
        return None

    def get_active_on_date(self):
        """
        Returns a date for the "active on" field.
        """
        year = self.year_entry.get_text()
        month = self.month_entry.get_text()
        day = self.day_entry.get_text()

        active_on_date = datetime.date(int(year), int(month),
                int(day))
        return active_on_date
        
    def display_pools(self):
        """
        Re-display the list of pools last queried, based on current filter options.
        """
        self.subs_store.clear()

        merged_pools = self.pool_stash.merge_pools(
                compatible=self.show_compatible(),
                overlapping=self.show_overlapping(),
                uninstalled=self.show_uninstalled(),
                text=self.get_filter_text())

        for entry in merged_pools.values():
            self.subs_store.append([
                entry.product_name, 
                entry.bundled_products,
                len(entry.pools),
                entry.quantity,
                entry.quantity - entry.consumed,
                entry.product_id,
                entry.pools[0]['id'], # not displayed, just for lookup later
                entry, # likewise not displayed, for subscription
        ])

    def _add_column(self, name, order):
        column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)
        self.subs_treeview.append_column(column)

    def get_content(self):
        return self.all_subs_vbox

    def get_label(self):
        return _("All Available Subscriptions")

    def search_button_clicked(self, widget):
        """
        Reload the subscriptions from the server when the Search button
        is clicked.
        """
        try:
            self.pool_stash.refresh(self.get_active_on_date())
            self.display_pools()
        except Exception, e:
            handle_gui_exception(e, _("Error fetching subscriptions from server: %s"))

    def date_select_button_clicked(self, widget):
        self.date_selector.show()

    def filters_changed(self, widget):
        """
        Callback used by several widgets related to filtering, anytime
        something changes, we re-display based on the latest choices.
        """
        log.debug("filters changed")
        self.display_pools()

    def active_on_date_changed(self, widget):
        """
        Callback for the date selector whenever the user has selected a new
        active on date.
        """
        year, month, day = widget.get_date()
        month += 1 # this starts at 0
        self._set_active_on_text(year, month, day)

    def _set_active_on_text(self, year, month, day):
        self.day_entry.set_text(str(day))
        self.month_entry.set_text(str(month))
        self.year_entry.set_text(str(year))


    def _contract_selected(self, pool):
        self._contract_selection_cancelled()
        try:
            self.backend.uep.bindByEntitlementPool(self.consumer.uuid, pool['id'])
            managergui.fetch_certificates()
        except Exception, e:
            handle_gui_exception(e, _("Error getting subscription: %s"))

        #Force the search results to refresh with the new info
        self.search_button_clicked(None)

    def _contract_selection_cancelled(self):
        self.contract_selection.destroy()
        self.contract_selection = None

    def subscribe_button_clicked(self, button):
        model, tree_iter = self.subs_treeview.get_selection().get_selected()
        pools = model.get_value(tree_iter, MERGED_POOLS_INDEX)
      
        # Decide if we need to show the contract selection dialog or not.
        # if there's just one pool, shortcut right to the callback that the
        # dialog would have run.
        if len(pools.pools) == 1:
            self._contract_selected(pools.pools[1])

        self.contract_selection = ContractSelectionWindow(
                self._contract_selected, self._contract_selection_cancelled)

        for pool in pools.pools:
            self.contract_selection.add_pool(pool)

        self.contract_selection.show()

    def update_sub_details(self, widget):
        """ Shows details for the current selected pool. """
        model, tree_iter = widget.get_selected()
        if tree_iter:
            product_name = model.get_value(tree_iter, PRODUCT_NAME_INDEX)
            pool_id = model.get_value(tree_iter, POOL_ID_INDEX)
            provided = self._load_product_data(pool_id)
            self.sub_details.show(product_name, products=provided)
            
        self.subscribe_button.set_sensitive(tree_iter != None)

    def _load_product_data(self, pool_id):
        pool = self.pool_stash.all_pools[pool_id]
        provided_products = []
        log.debug(pool)
        for product in pool['providedProducts']:
            provided_products.append((product['productName'], product['productId']))
        return provided_products

