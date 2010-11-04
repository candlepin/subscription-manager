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
import logging
import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)
import managerlib

from facts import Facts
from widgets import SubDetailsWidget
from dateselect import DateSelector

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


class AllSubscriptionsTab(object):

    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer
        self.facts = facts

        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        self.all_subs_xml = gtk.glade.XML(ALL_SUBS_GLADE)
        self.all_subs_vbox = self.all_subs_xml.get_widget('all_subs_vbox')

        today = datetime.date.today()
        self.date_selector = DateSelector(self.active_on_date_changed, initial_date=today)

        self.subs_store = gtk.ListStore(str, str, str, str, str, str, str)
        self.subs_treeview = self.all_subs_xml.get_widget('all_subs_treeview')
        self.subs_treeview.set_model(self.subs_store)
        self._add_column(_("Subscription"), PRODUCT_NAME_INDEX)
        self._add_column(_("# Bundled Products"), BUNDLED_COUNT_INDEX)
        self._add_column(_("Total Contracts"), POOL_COUNT_INDEX)
        self._add_column(_("Total Subscriptions"), QUANTITY_INDEX)
        self._add_column(_("Available Subscriptions"), AVAIL_INDEX)

        self.no_hw_match_checkbutton = self.all_subs_xml.get_widget(
                'match_hw_checkbutton')
        self.not_installed_checkbutton = self.all_subs_xml.get_widget(
                'not_installed_checkbutton')
        self.contains_text_checkbutton = self.all_subs_xml.get_widget(
                'contains_text_checkbutton')
        self.contains_text_entry = self.all_subs_xml.get_widget(
                'contain_text_entry')
        self.sub_details = SubDetailsWidget(show_contract=False)
        self.all_subs_vbox.pack_end(self.sub_details.get_widget())

        self.active_on_checkbutton = self.all_subs_xml.get_widget('active_on_checkbutton')
        self.active_on_entry = self.all_subs_xml.get_widget('active_on_entry')

        # Set the date filter to todays date by default:
        self.active_on_entry.set_text(today.strftime("%Y-%m-%d"))

        self.all_subs_xml.signal_autoconnect({
            "on_search_button_clicked": self.search_button_clicked,
            "on_date_select_button_clicked": self.date_select_button_clicked,
            "on_match_hw_checkbutton_clicked": self.filters_changed,
            "on_not_installed_checkbutton_clicked": self.filters_changed,
            "on_contains_text_checkbutton_clicked": self.filters_changed,
            "on_contain_text_entry_changed": self.filters_changed,
        })
        self.subs_treeview.get_selection().connect('changed', self.update_sub_details)


    def include_incompatible(self):
        """ Return True if we're to include pools which failed a rule check. """
        return self.no_hw_match_checkbutton.get_active()

    def include_uninstalled(self):
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
        text = self.active_on_entry.get_text()
        year, month, day = text.split('-')
        active_on_date = datetime.date(int(year), int(month),
                int(day))
        return active_on_date
        
    def display_pools(self):
        """
        Re-display the list of pools last queried, based on current filter options.
        """
        self.subs_store.clear()

        merged_pools = self.pool_stash.merge_pools(
                incompatible=self.include_incompatible(),
                uninstalled=self.include_uninstalled(),
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
        log.debug("Search button clicked.")
        log.debug("   include hw mismatch = %s" % self.include_incompatible())
        log.debug("   include uninstalled = %s" % self.include_uninstalled())
        log.debug("   contains text = %s" % self.get_filter_text())
        self.pool_stash.refresh(self.get_active_on_date())
        self.display_pools()

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
        self.active_on_entry.set_text("%s-%s-%s" % (year, month, day))

    def update_sub_details(self, widget):
        """ Shows details for the current selected pool. """
        model, tree_iter = widget.get_selected()
        if tree_iter:
            product_name = model.get_value(tree_iter, PRODUCT_NAME_INDEX)
            pool_id = model.get_value(tree_iter, POOL_ID_INDEX)
            provided = self._load_product_data(pool_id)
            self.sub_details.show(product_name, products=provided)


    def _load_product_data(self, pool_id):
        pool = self.pool_stash.all_pools[pool_id]
        provided_products = []
        log.debug(pool)
        # NOTE: Not happy about this, but the only way we can get a friendly
        # name for each provided product is to ask for it, the pool only
        # carries the ID:
        for prod_id in pool['providedProductIds']:
            product = self.backend.uep.getProduct(prod_id)
            provided_products.append((product['name'], prod_id))
        return provided_products

