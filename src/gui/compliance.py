# Subscription Manager Compliance Assistant
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
import gtk
import locale
import logging
import gettext
from datetime import date

_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

import certificate
import certlib
import managerlib
import storage
from dateselect import DateSelector
from widgets import SubDetailsWidget


prefix = os.path.dirname(__file__)
COMPLIANCE_GLADE = os.path.join(prefix, "data/compliance.glade")

class MappedListTreeView(gtk.TreeView):

    def add_toggle_column(self, name, column_number, callback):
        toggle_renderer = gtk.CellRendererToggle()
        toggle_renderer.set_property("activatable", True)
        toggle_renderer.set_radio(False)
        toggle_renderer.connect("toggled", callback)
        column = gtk.TreeViewColumn(name, toggle_renderer, active=column_number)
        self.append_column(column)

    def add_column(self, name, column_number, expand=False):
        text_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(name, text_renderer, text=column_number)
        self.store = self.get_model()
        if expand:
            column.set_expand(True)
        else:
            column.add_attribute(text_renderer, 'xalign', self.store['align'])
            
#        column.add_attribute(text_renderer, 'cell-background', 
#                             self.store['background'])

        self.append_column(column)

class ComplianceAssistant(object):

    """ Compliance Assistant GUI window. """
    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        self.product_dir = certlib.ProductDirectory()
        self.entitlement_dir = certlib.EntitlementDirectory()

        self.compliance_xml = gtk.glade.XML(COMPLIANCE_GLADE)
        self.compliance_label = self.compliance_xml.get_widget(
            "compliance_label")
        self.compliant_today_label = self.compliance_xml.get_widget(
            "compliant_today_label")

        # Setup initial last compliant date:
        self.last_compliant_date = self._find_last_compliant()
        self.month_entry = self.compliance_xml.get_widget("month_entry")
        self.day_entry = self.compliance_xml.get_widget("day_entry")
        self.year_entry = self.compliance_xml.get_widget("year_entry")
        if self.last_compliant_date:
            self._set_noncompliant_date(self.last_compliant_date)
        else:
            self._set_noncompliant_date(date.today())
        self.noncompliant_date_radiobutton = self.compliance_xml.get_widget("noncompliant_date_radiobutton")


        uncompliant_type_map = {'active':bool,
                                'product_name':str,
                                'contract':str,
                                'end_date':str,
                                'entitlement_id':str,
                                'product_id':str,
                                'align':float}
       
        self.window = self.compliance_xml.get_widget('compliance_assistant_window')
        self.window.connect('delete_event', self.hide)
        self.uncompliant_store = storage.MappedListStore(uncompliant_type_map)
        self.uncompliant_treeview = MappedListTreeView(self.uncompliant_store)

        self.uncompliant_treeview.add_toggle_column(None,
                                                    self.uncompliant_store['active'],
                                                    self._on_uncompliant_active_toggled)
        self.uncompliant_treeview.add_column("Product",
                self.uncompliant_store['product_name'], True)
        self.uncompliant_treeview.add_column("Contract",
                self.uncompliant_store['contract'], True)
        self.uncompliant_treeview.add_column("Expiration",
                self.uncompliant_store['end_date'], True)
        self.uncompliant_treeview.set_model(self.uncompliant_store)
        vbox = self.compliance_xml.get_widget("uncompliant_vbox")
        vbox.pack_end(self.uncompliant_treeview)
        self.uncompliant_treeview.show()

        subscriptions_type_map = {'product_name':str, 
                                  'total_contracts': float,
                                  'total_subscriptions':float,
                                  'available_subscriptions':float,
                                  'align': float,
                                  'pool_id':str}

        self.subscriptions_store = storage.MappedListStore(subscriptions_type_map)
        self.date_selector = DateSelector(self._compliance_date_selected)

        self.subscriptions_treeview = MappedListTreeView(self.subscriptions_store)
        self.subscriptions_treeview.add_column("Product Name",
                self.subscriptions_store['product_name'], True)
        self.subscriptions_treeview.add_column("Total Contracts",
                self.subscriptions_store['total_contracts'], True)
        self.subscriptions_treeview.add_column("Total Subscriptions",
                self.subscriptions_store['total_subscriptions'], True)
        self.subscriptions_treeview.add_column("Available Subscriptions",
                self.subscriptions_store['available_subscriptions'], True)

        self.subscriptions_treeview.set_model(self.subscriptions_store)
        self.subscriptions_treeview.get_selection().connect('changed',
                self._update_sub_details)

        vbox = self.compliance_xml.get_widget("subscriptions_vbox")
        vbox.pack_start(self.subscriptions_treeview)
        self.subscriptions_treeview.show()

        self.sub_details = SubDetailsWidget(show_contract=False)
        vbox.pack_start(self.sub_details.get_widget())

        self.first_noncompliant_radiobutton = \
            self.compliance_xml.get_widget('first_noncompliant_radiobutton')
        self.first_noncompliant_radiobutton.set_active(True)
        self.noncompliant_date_radiobutton = \
            self.compliance_xml.get_widget('noncompliant_date_radiobutton')

        self.compliance_xml.signal_autoconnect({
            "on_compliance_date_button_clicked": self._date_select_button_clicked,
            "on_first_noncompliant_radiobutton_toggled": self._reload_screen,
            "on_noncompliant_date_radiobutton_toggled": self._reload_screen,
        })

    def _compliance_date_selected(self, widget):
        """
        Callback for the date selector to execute when the date has been chosen.
        """
        year, month, day = widget.get_date()
        month += 1 # this starts at 0 in GTK
        d = date(year, month, day)
        self._set_noncompliant_date(d)
        self.noncompliant_date_radiobutton.set_active(True)
        self._reload_screen()

    def _date_select_button_clicked(self, widget):
        self.date_selector.show()

    def _get_noncompliant_date(self):
        """
        Returns a datetime.datetime object for the non-compliant date to use based on current
        state of the GUI controls.
        """
        if self.first_noncompliant_radiobutton.get_active():
            return self.last_compliant_date
        else:
            return datetime.datetime(int(self.year_entry.get_text()),
                                     int(self.month_entry.get_text()),
                                     int(self.day_entry.get_text()), tzinfo=certificate.GMT())

    def _find_last_compliant(self):
        """
        Find the first date where an entitlement will be uncompliant.
        """
        # TODO: what about products installed but not covered by *any* entitlement?
        # TODO: should we be listing valid? does this work if everything is already out of compliance?
        # TODO: setting a member variable here that isn't used anywhere else, should keep this local unless needed
        # TODO: needs unit testing imo, probably could be moved to a standalone method for that purpose
        self.valid_subs = certlib.EntitlementDirectory().listValid()

        print "valid_subs", self.valid_subs
        # FIXME: remote debug
        for valid_sub in self.valid_subs:
            print "valid_range", valid_sub.validRange().end(), type(valid_sub.validRange().end())

        def get_date(sub):
            return sub.validRange().end()

        self.valid_subs.sort(key=get_date)

        if self.valid_subs:
            return self.valid_subs[0].validRange().end()
        else:
            return date.today()

    def _display_subscriptions(self):
        self.subscriptions_store.clear()


        selection = self.uncompliant_treeview.get_selection()
        print "selection", selection, "foo"



        for row in self.uncompliant_treeview:
            print "row", row, len(row)
            print row[0]
            print row[1]
            print row[2]
        
#        print "selected", selection.get_selected()
        
        fake_subscriptions = [{"product_name":"Awesomeness", "total_contracts":1000, "total_subscriptions":222, "available_subscriptions":4, "align":0.0, "pool_id": "fakepoolid"}]

        
        for fake_subscription in fake_subscriptions:
            self.subscriptions_store.add_map(fake_subscription)

    def _display_uncompliant(self):
        uncompliant = []
        if self.last_compliant_date:
            uncompliant = self.entitlement_dir.listExpiredOnDate(date=self._get_noncompliant_date())
            
        noncompliant_products = self.product_dir.listExpiredOnDate(date=self._get_noncompliant_date())

        # TODO: For testing, this is querying subs from the server. This method
        # will eventually calculate uncompliant products installed on the machine.
        # (and likely soon to expire entitlements that are for products not installed)

        # These display the list of products uncompliant on the selected date:
        self.uncompliant_store.clear()
 
        # find installed products with no entitlements
        entitlement_filter = managerlib.EntitlementFilter()
        noncompliant_installed_products = entitlement_filter.filter_entitlements_by_uninstalled()

        # add all the installed but not entitled products
        na = _("N/A")
        for product in noncompliant_installed_products:
            self.uncompliant_store.add_map({'active':False,
                                            'product_name':product.getProduct().getName(),
                                            'contract':na,
                                            'end_date':na,
                                            'entitlement_id':None,
                                            'product_id':product.getProduct().getHash(),
                                            'align':0.0})

        for product in noncompliant_products:
            entitlement = self.entitlement_dir.findByProduct(product.getProduct().getHash())
            if entitlement is None:
                print "No entitlement found for ", product.getProduct().getName()
                continue

            self.uncompliant_store.add_map({'active':False,
                                            'product_name':product.getProduct().getName(),
                                            'contract':entitlement.getOrder().getNumber(),
                                            # is end_date when the cert expires or the orders end date? is it differnt?
                                            'end_date':'%s' % self.format_date(entitlement.validRange().end()),
                                            'entitlement_id':entitlement.serialNumber(),
                                            'product_id':product.getProduct().getHash(),
                                            'align':0.0})
        

    def _on_uncompliant_active_toggled(self, cell, path):
        print "toggled"
        treeiter = self.uncompliant_store.get_iter_from_string(path)
        item = self.uncompliant_store.get_value(treeiter, 0)
        self.uncompliant_store.set_value(treeiter, 0, not item)


#        print self.uncompliant_store.next()
#        print self.uncompliant_store.next()
        for row in self.uncompliant_store:
#            print "row", row, len(row)
#            print row[0], row[1], row[2], row[3], row[4], row[5]
            #print row[self.uncompliant_store['pool_id']]
            #print row[self.uncompliant_store['product_name']]
            print row[self.uncompliant_store['product_id']]
            print self.entitlement_dir.findByProduct(row[self.uncompliant_store['product_id']])


    def show(self):
        """
        Called by the main window when this page is to be displayed.
        """
        self._reload_screen()
        self.window.show()

    def _reload_screen(self, widget=None):
        """
        Draws the entire screen, called when window is shown, or something
        changes and we need to refresh.
        """
        log.debug("reloading screen")
        # end date of first subs to expire
        
        self.last_compliant_date = self._find_last_compliant()


#        for product_cert in self.product_dir.list():
            
        self.pool_stash.refresh(active_on=self._get_noncompliant_date())

        if self.last_compliant_date:
            formatted = self.format_date(self.last_compliant_date)
            self.compliance_label.set_label(
                    _("All software is in compliance until %s.") % formatted)
            self.first_noncompliant_radiobutton.set_label(
                    _("%s (first date of non-compliance)") % formatted)

        self._display_uncompliant()
        self._display_subscriptions()

    def format_date(self, date):
        return date.strftime(locale.nl_langinfo(locale.D_FMT))

    def hide(self, widget, event, data=None):
        self.window.hide()
        return True

    def _update_sub_details(self, widget):
        """ Shows details for the current selected pool. """
        model, tree_iter = widget.get_selected()
        if tree_iter:
            product_name = model.get_value(tree_iter, self.subscriptions_store['product_name'])
            # TODO: need to show provided products here once we have a pool stash:
            self.sub_details.show(product_name)

    def _set_noncompliant_date(self, noncompliant_date):
        self.month_entry.set_text(str(noncompliant_date.month))
        self.day_entry.set_text(str(noncompliant_date.day))
        self.year_entry.set_text(str(noncompliant_date.year))
