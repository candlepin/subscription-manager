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
import progress
import gettext
_ = gettext.gettext

from rhsm.logutil import getLogger
log = getLogger(__name__)
import managergui
import managerlib

import widgets
import storage
import async
from utils import handle_gui_exception
from contract_selection import ContractSelectionWindow

prefix = os.path.dirname(__file__)
ALL_SUBS_GLADE = os.path.join(prefix, "data/allsubs.glade")


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

        self.date_picker = widgets.DatePicker(today)
        date_picker_hbox = self.all_subs_xml.get_widget("date_picker_hbox")
        date_picker_hbox.pack_start(self.date_picker)
        date_picker_hbox.show_all()

        self.subs_store = storage.MappedListStore({
            'product_name': str,
            'bundled_count': str,
            'pool_count': str,
            'quantity': str,
            'available': str,
            'product_id': str,
            'pool_id': str,
            'merged_pools': gobject.TYPE_PYOBJECT,
        })

        self.subs_treeview = self.all_subs_xml.get_widget('all_subs_treeview')
        self.subs_treeview.set_model(self.subs_store)
        self._add_column(_("Subscription"), self.subs_store['product_name'])
        self._add_column(_("# Bundled Products"), self.subs_store['bundled_count'])
        self._add_column(_("Total Contracts"), self.subs_store['pool_count'])
        self._add_column(_("Total Subscriptions"), self.subs_store['quantity'])
        self._add_column(_("Available Subscriptions"), self.subs_store['available'])

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
        self.sub_details = widgets.SubDetailsWidget(show_contract=False)
        self.all_subs_vbox.pack_start(self.sub_details.get_widget(), expand=False)

        self.contract_selection = None

        self.active_on_checkbutton = self.all_subs_xml.get_widget('active_on_checkbutton')

        self.subscribe_button = self.all_subs_xml.get_widget('subscribe_button')

        self.all_subs_xml.signal_autoconnect({
            "on_search_button_clicked": self.search_button_clicked,
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
            self.subs_store.add_map({
                'product_name': entry.product_name, 
                'bundled_count': entry.bundled_products,
                'pool_count': len(entry.pools),
                'quantity': entry.quantity,
                'available': entry.quantity - entry.consumed,
                'product_id': entry.product_id,
                'pool_id': entry.pools[0]['id'], # not displayed, just for lookup later
                'merged_pools': entry, # likewise not displayed, for subscription
        })

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
            async_stash = async.AsyncPool(self.pool_stash)
            async_stash.refresh(self.date_picker.date, self._update_display)
            # show pulsating progress bar while we wait for results
            self.pb = progress.Progress(
                    _("Searching for subscriptions. Please wait."))
            self.timer = gobject.timeout_add(100, self.pb.pulse)
            self.pb.set_parent_window(self.all_subs_vbox.get_parent_window().get_user_data())
        except Exception, e:
            handle_gui_exception(e, _("Error fetching subscriptions from server: %s"))

    def _update_display(self):
        # should probably use the params instead
        self.display_pools()
        if self.pb:
            self.pb.hide()
            gobject.source_remove(self.timer)
            self.timer = 0

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
            managergui.fetch_certificates()
        except Exception, e:
            handle_gui_exception(e, _("Error getting subscription: %s"))

        #Force the search results to refresh with the new info
        self.search_button_clicked(None)

    def _contract_selection_cancelled(self):
        if self.contract_selection:
            self.contract_selection.destroy()
        self.contract_selection = None

    def subscribe_button_clicked(self, button):
        model, tree_iter = self.subs_treeview.get_selection().get_selected()
        pools = model.get_value(tree_iter, self.subs_store['merged_pools'])
      
        # Decide if we need to show the contract selection dialog or not.
        # if there's just one pool, shortcut right to the callback that the
        # dialog would have run.
        if len(pools.pools) == 1:
            self._contract_selected(pools.pools[0])
            return

        self.contract_selection = ContractSelectionWindow(
                self._contract_selected, self._contract_selection_cancelled)

        for pool in pools.pools:
            self.contract_selection.add_pool(pool)

        self.contract_selection.show()

    def update_sub_details(self, widget):
        """ Shows details for the current selected pool. """
        model, tree_iter = widget.get_selected()
        if tree_iter:
            product_name = model.get_value(tree_iter,
                    self.subs_store['product_name'])
            pool_id = model.get_value(tree_iter, self.subs_store['pool_id'])
            provided = self.pool_stash.lookup_provided_products(pool_id)
            self.sub_details.show(product_name, products=provided)
        else:
            self.sub_details.clear()
            
        self.subscribe_button.set_sensitive(tree_iter != None)

