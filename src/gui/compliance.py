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

_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

import certlib
import managerlib
import storage
from dateselect import DateSelector
from widgets import SubDetailsWidget


prefix = os.path.dirname(__file__)
COMPLIANCE_GLADE = os.path.join(prefix, "data/compliance.glade")

PRODUCT_NAME_INDEX = 0
CONTRACT_INDEX = 1
EXPIRATION_INDEX = 2

class MappedListTreeView(gtk.TreeView):
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
        self.compliance_xml = gtk.glade.XML(COMPLIANCE_GLADE)
        self.window = self.compliance_xml.get_widget('compliance_assistant_window')
        self.uncompliant_store = gtk.ListStore(str, str, str)
        self.uncompliant_treeview = self.compliance_xml.get_widget(
                'uncompliant_products_treeview')
        self.uncompliant_treeview.set_model(self.uncompliant_store)
        self._display_uncompliant()


        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        # end date of first subs to expire 
        self.last_compliant_date = self._find_last_compliant()

        self.compliance_label = self.compliance_xml.get_widget(
            "compliance_label")

        self.compliance_label.set_label(_("All software is in compliance until %s.") % 
                                             self.last_compliant_date.strftime(locale.nl_langinfo(locale.D_FMT)))

        subscriptions_type_map = {'product_name':str, 
                                  'total_contracts': float,
                                  'total_subscriptions':float,
                                  'available_subscriptions':float,
                                  'align': float}

        self.subscriptions_store = storage.MappedListStore(subscriptions_type_map)

        self.subscriptions_treeview = MappedListTreeView(self.subscriptions_store)
        self.subscriptions_treeview.set_model(self.subscriptions_store)
        self._display_subscriptions()

        vbox = self.compliance_xml.get_widget("vbox1")
        vbox.pack_end(self.subscriptions_treeview)
        self.subscriptions_treeview.show()
        


    # FIXME: should this methods on CertificateDirectory? 
    def _find_last_compliant(self):
        self.valid_subs = certlib.EntitlementDirectory().listValid()

        # FIXME: remote debug
        for valid_sub in self.valid_subs:
            print "valid_range", valid_sub.validRange().end(), type(valid_sub.validRange().end())

        def get_date(sub):
            return sub.validRange().end()

        self.valid_subs.sort(key=get_date)

        if self.valid_subs:
            return self.valid_subs[0].validRange().end()

    def _display_subscriptions(self):
#        self.subscriptions_store.clear()

        self.subscriptions_treeview.add_column("Product Name", 
                                               self.subscriptions_store['product_name'], True)
        self.subscriptions_treeview.add_column("Total Contracts",
                                               self.subscriptions_store['total_contracts'], True)
        self.subscriptions_treeview.add_column("Total Subscriptions",
                                               self.subscriptions_store['total_subscriptions'], True)
        self.subscriptions_treeview.add_column("Available Subscriptions",
                                               self.subscriptions_store['available_subscriptions'], True)

        fake_subscriptions = [{"product_name":"Awesomeness", "total_contracts":1000, "total_subscriptions":222, "available_subscriptions":4, "align":0.0}]
#                              ("Cheese", 4.0, 3.0, 2.0, 0.0),
#                              ("dude, lasers", 10.0, 10.0, 10.0, 0.0)]
        
        for fake_subscription in fake_subscriptions:
            print fake_subscription
            self.subscriptions_store.add_map(fake_subscription)

    def _display_uncompliant(self):
        # These display the list of products uncompliant on the selected date:
        self.uncompliant_store.clear()
        self._add_column(_('Product'), PRODUCT_NAME_INDEX)
        self._add_column(_('Contract'), CONTRACT_INDEX)
        self._add_column(_('Expiration'), EXPIRATION_INDEX)

        self.uncompliant_store.append(['Fake Product 1', 'FAKE01010010', '2010-01-01'])
        self.uncompliant_store.append(['Fake Product 2', 'N/A', 'N/A'])

        # Dummy data for now:

    def _display_providing_subs(self):
        pass

    def show(self):
        self.window.show()

    def _add_column(self, name, order):
        column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)
        self.uncompliant_treeview.append_column(column)
