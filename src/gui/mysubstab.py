
#
# GUI Module for standalone subscription-manager - 'My Subscriptions' tab
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Justin Harris <jharris@redhat.com>
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

from datetime import datetime, timedelta
from certlib import EntitlementDirectory, ProductDirectory
from certificate import GMT
from managerlib import formatDate

import widgets

import logutil
log = logutil.getLogger(__name__)

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

# Color constants for background rendering
YELLOW = '#FFFB82'
RED = '#FFAF99'

# subscription_store indices
SUBSCRIPTION = 0
INSTALLED_PERCENT = 1
INSTALLED_TEXT = 2
CONTRACT = 3
START_DATE = 4
EXPIRATION_DATE = 5
SERIAL = 6
ALIGN = 7
BACKGROUND = 8

WARNING_DAYS = 6 * 7   # 6 weeks * 7 days / week

class MySubscriptionsTab(widgets.GladeWidget):

    def __init__(self, backend, consumer, facts):
        """
        Create a new 'My Subscriptions' tab.
        """
        widget_names = ['subscription_view', 'content']
        super(MySubscriptionsTab, self).__init__('mysubs.glade', widget_names)
        
        self.backend = backend
        self.consumer = consumer

        self.sub_details = widgets.SubDetailsWidget()

        # Put the details widget in the middle
        details = self.sub_details.get_widget()
        self.content.add(details)

        selection = self.subscription_view.get_selection()
        selection.connect('changed', self.update_details)

        # Set up the model
        self.subscription_store = gtk.ListStore(str, float, str, str, str, 
            str, str, float, str)
        self.subscription_view.set_model(self.subscription_store)

        def add_column(name, column_number, expand=False):
            text_renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name, text_renderer, text=column_number)
            if expand:
                column.set_expand(True)
            else:
                # This is probably too hard-coded
                column.add_attribute(text_renderer, 'xalign', ALIGN)

            column.add_attribute(text_renderer, 'cell-background', BACKGROUND)

            self.subscription_view.append_column(column)

        # Set up columns on the view
        add_column(_("Subscription"), SUBSCRIPTION, True)
        products_column = gtk.TreeViewColumn(_("Installed Products"),
                                             gtk.CellRendererProgress(),
                                             value=INSTALLED_PERCENT,
                                             text=INSTALLED_TEXT)
        self.subscription_view.append_column(products_column)

        add_column(_("Contract"), CONTRACT)
        add_column(_("Start Date"), START_DATE)
        add_column(_("Expiration Date"), EXPIRATION_DATE)

        self.update_subscriptions()


    def update_subscriptions(self):
        """
        Pulls the entitlement certificates and updates the subscription model.
        """
        entcerts = EntitlementDirectory().list()

        for cert in entcerts:
            order = cert.getOrder()
            products = cert.getProducts()
            installed = self._get_installed(products)

            # Initialize an entry list of the proper length
            columns = self.subscription_store.get_n_columns()
            entry = [None for i in range(columns)]
            
            entry[SUBSCRIPTION] = order.getName()
            entry[INSTALLED_PERCENT] = \
                self._calculate_percentage(installed, products)
            entry[INSTALLED_TEXT] = '%s / %s' % (len(installed), len(products))
            entry[CONTRACT] = order.getContract()
            entry[START_DATE] = formatDate(order.getStart())
            entry[EXPIRATION_DATE] = formatDate(order.getEnd())
            entry[SERIAL] = cert.serialNumber()
            entry[ALIGN] = 0.5         # Center horizontally
            entry[BACKGROUND] = self._get_background_color(cert)
            
            self.subscription_store.append(entry)

    def get_content(self):
        return self.content

    def get_label(self):
        return _("My Subscriptions")

    def update_details(self, treeselection):
        """
        Updates the 'Subscription Details' panel with the currently selected
        subscription.
        """
        model, tree_iter = treeselection.get_selected()

        if tree_iter is None:
            return

        # Load the entitlement certificate for the selected row:
        serial = model.get_value(tree_iter, SERIAL)
        cert = EntitlementDirectory().find(int(serial))
        order = cert.getOrder()
        products = [(product.getName(), product.getHash())
                        for product in cert.getProducts()]

        self.sub_details.show(order.getName(), 
                              contract=order.getContract() or "", 
                              start=str(formatDate(order.getStart())), 
                              end=str(formatDate(order.getEnd())),
                              products=products)

    def _get_background_color(self, entitlement_cert):
        date_range = entitlement_cert.validRange()
        now = datetime.now(GMT())

        if date_range.end() < now:
            return RED

        if date_range.end() - timedelta(days=WARNING_DAYS) < now:
            return YELLOW

    def _calculate_percentage(self, subset, full_set):
        return (float(len(subset)) / len(full_set)) * 100

    def _get_installed(self, products):
        installed_dir = ProductDirectory()
        installed_products = []

        for product in products:
            installed = installed_dir.findByProduct(product.getHash())

            if installed:
                installed_products.append(installed)

        return installed_products
