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
import gtk
import gobject
import locale
import logging
import gettext
from datetime import date, time, datetime

_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

import certificate
import certlib
from certlib import find_last_compliant
import managerlib
import storage
from connection import RestlibException
from dateselect import DateSelector
from widgets import SubDetailsWidget
from utils import handle_gui_exception


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

        self.chosen_entitlements = []

        self.compliance_xml = gtk.glade.XML(COMPLIANCE_GLADE)
        self.compliance_label = self.compliance_xml.get_widget(
            "compliance_label")
        self.compliant_today_label = self.compliance_xml.get_widget(
            "compliant_today_label")

        # Setup initial last compliant date:
        self.last_compliant_date = find_last_compliant()
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
                                'entitlement':gobject.TYPE_PYOBJECT,
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
                                  'total_contracts':str,
                                  'total_subscriptions':str,
                                  'available_subscriptions':str,
                                  'align':float,
                                  'entitlement':gobject.TYPE_PYOBJECT,
                                  'pool_id':str}

        self.subscriptions_store = storage.MappedListStore(subscriptions_type_map)
        self.date_selector = DateSelector(self._compliance_date_selected)

        self.subscriptions_treeview = MappedListTreeView(self.subscriptions_store)
        self.subscriptions_treeview.add_column("Subscription Name",
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
        Returns a datetime object for the non-compliant date to use based on current
        state of the GUI controls.
        """
        if self.first_noncompliant_radiobutton.get_active():
            return self.last_compliant_date
        else:
            return datetime(int(self.year_entry.get_text()),
                            int(self.month_entry.get_text()),
                            int(self.day_entry.get_text()), tzinfo=certificate.GMT())

    def _display_subscriptions(self):
        self.subscriptions_store.clear()

        selection = self.uncompliant_treeview.get_selection()

#        pools = self.pool_stash.filter_pools(compatible=True, overlapping=False, uninstalled=False, text=None)
#        self.pool_stash.refresh(active_on=self._get_noncompliant_date())
#        pool_filter = managerlib.PoolFilter()

        subscriptions_map = {}
        # this should be roughly correct for locally manager certs, needs
        # remote subs/pools as well
        for entitlement in self.chosen_entitlements:
#            pools_for_products = pool_filter.filter_pools_by_products(pools, entitlement.getProducts())
#            print pools_for_products

            for product in entitlement.getProducts():
                subscriptions_map[product.getHash()] = {'product_name':product.getName(),
                                                        # how many ents match this product?
                                                        'total_contracts':entitlement.getOrder().getQuantity(),
                                                        # this should eventually be the total of all the ents/pools for this product
                                                        'total_subscriptions':entitlement.getOrder().getQuantity(),
                                                        # pretty sure this is wrong
                                                        'available_subscriptions':entitlement.getOrder().getQuantityUsed(),
                                                        'entitlement': entitlement,
                                                        'align':0.0}

        for key in subscriptions_map:
            self.subscriptions_store.add_map(subscriptions_map[key])

    def _display_uncompliant(self):
        uncompliant = []
        if self.last_compliant_date:
            noncompliant_entitlements = self.entitlement_dir.listExpiredOnDate(date=self._get_noncompliant_date())



        noncompliant_products = []
        for noncompliant_entitlement in noncompliant_entitlements:
            noncompliant_products.append(noncompliant_entitlement.getProduct())
#        noncompliant_products = self.product_dir.listExpiredOnDate(date=self._get_noncompliant_date())

        # These display the list of products uncompliant on the selected date:
        self.uncompliant_store.clear()

        # find installed products with no entitlements
        entitlement_filter = managerlib.EntitlementFilter()
        noncompliant_installed_products = entitlement_filter.installed_products_without_entitlements()

        # add all the installed but not entitled products
        na = _("N/A")
        for product in noncompliant_installed_products:
            self.uncompliant_store.add_map({'active':False,
                                            'product_name':product.getProduct().getName(),
                                            'contract':na,
                                            'end_date':na,
                                            'entitlement_id':None,
                                            'entitlement':None,
                                            'product_id':product.getProduct().getHash(),
                                            'align':0.0})

        # installed and out of compliance
        for product in noncompliant_products:
            entitlement = self.entitlement_dir.findByProduct(product.getHash())
            if entitlement is None:
                print "No entitlement found for ", product.getName()
                continue

            self.uncompliant_store.add_map({'active':False,
                                            'product_name':product.getName(),
                                            'contract':entitlement.getOrder().getNumber(),
                                            # is end_date when the cert expires or the orders end date? is it differnt?
                                            'end_date':'%s' % self.format_date(entitlement.validRange().end()),
                                            'entitlement_id':entitlement.serialNumber(),
                                            'entitlement':entitlement,
                                            'product_id':product.getHash(),
                                            'align':0.0})


    def _on_uncompliant_active_toggled(self, cell, path):
        treeiter = self.uncompliant_store.get_iter_from_string(path)
        item = self.uncompliant_store.get_value(treeiter, self.uncompliant_store['active'])
        self.uncompliant_store.set_value(treeiter, self.uncompliant_store['active'], not item)

        # chosen is a weird word, but selected in this context means something else
        self.chosen_entitlements = []
        for row in self.uncompliant_store:
            if row[self.uncompliant_store['active']]:
                for entitlement in self.entitlement_dir.findAllByProduct(row[self.uncompliant_store['product_id']]):
                    self.chosen_entitlements.append(entitlement)

        # refresh subscriptions
        self._display_subscriptions()


    def show(self):
        """
        Called by the main window when this page is to be displayed.
        """
        try:
            self._reload_screen()
            self.window.show()
        except RestlibException, e:
            handle_gui_exception(e, _("Error fetching subscriptions from server: %s"))
        except Exception, e:
            handle_gui_exception(e, _("Error displaying Compliance Assistant. Please see /var/log/rhsm/rhsm.log for more information."))

    def _reload_screen(self, widget=None):
        """
        Draws the entire screen, called when window is shown, or something
        changes and we need to refresh.
        """
        log.debug("reloading screen")
        # end date of first subs to expire

        self.last_compliant_date = find_last_compliant()


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

            entitlement = model.get_value(tree_iter, self.subscriptions_store['entitlement'])
            products_list = [(product.getName(), product.getHash()) \
                             for product in entitlement.getProducts()]

            self.sub_details.show(product_name,
                                  contract=entitlement.getOrder().getContract(),
                                  start=entitlement.validRange().begin(),
                                  end=entitlement.validRange().end(),
                                  account=entitlement.getOrder().getAccountNumber(),
                                  products=products_list)

    def _set_noncompliant_date(self, noncompliant_date):
        self.month_entry.set_text(str(noncompliant_date.month))
        self.day_entry.set_text(str(noncompliant_date.day))
        self.year_entry.set_text(str(noncompliant_date.year))

