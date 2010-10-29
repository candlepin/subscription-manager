
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

import datetime
import os
import gtk

from certlib import EntitlementDirectory, ProductDirectory
from managerlib import formatDate

from productstable import ProductsTable

import logutil
log = logutil.getLogger(__name__)

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/mysubs.glade")
SUB_DETAILS_XML = os.path.join(DIR, "data/subdetails.glade")

# Color constants for background rendering
YELLOW = '#FFFB82'
RED = '#FFAF99'

class SubDetailsWidget:

    def __init__(self):
        # TODO: move to a separate glade file?
        glade = gtk.glade.XML(SUB_DETAILS_XML)
        self.main_widget = glade.get_widget('sub_details_vbox')
        self.main_widget.unparent()

        self.subscription_text = glade.get_widget('subscription_text')
        self.contract_number_text = glade.get_widget('contract_number_text')
        self.start_date_text = glade.get_widget('start_date_text')
        self.expiration_date_text = glade.get_widget('expiration_date_text')
        self.bundled_products_view = glade.get_widget('products_view')

        self.bundled_products = ProductsTable(self.bundled_products_view)


    def show(self, name, contract=None, start=None, end=None, products=[]):
        """ 
        Show subscription details. 
        
        Start and end should be formatted strings, not actual date objects.
        Products is a list of tuples (or lists) of the form (name, id)
        """
        self.subscription_text.get_buffer().set_text(name)
        if contract:
            self.contract_number_text.get_buffer().set_text(contract)
        if start:
            self.start_date_text.get_buffer().set_text(start)
        if end:
            self.expiration_date_text.get_buffer().set_text(end)

        self.bundled_products.clear()
        for product in products:
            self.bundled_products.add_product(product[0], product[1])

    def clear(self):
        """ No subscription to display. """
        pass

    def get_widget(self):
        """ Returns the widget to be packed into a parent window. """
        return self.main_widget


class MySubscriptionsTab:

    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer

        glade = gtk.glade.XML(GLADE_XML)

        widget_names = ['subscription_view',
                        'content',
        ]
        self._pull_widgets(glade, widget_names)
        self.sub_details = SubDetailsWidget()

        # Put the details widget in the middle
        details = self.sub_details.get_widget()
        self.content.add(details)

        self.subscription_view.get_selection().connect('changed', self.update_details)

        # Set up the model
        self.subscription_store = gtk.ListStore(str, float, str, str, str, str, str, float, str)
        self.subscription_view.set_model(self.subscription_store)

        def add_column(name, column_number, expand=False):
            text_renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name, text_renderer, text=column_number)
            if expand:
                column.set_expand(True)
            else:
                # This is probably too hard-coded
                column.add_attribute(text_renderer, 'xalign', 7)

            column.add_attribute(text_renderer, 'cell-background', 8)

            self.subscription_view.append_column(column)

        # Set up columns on the view
        add_column(_("Subscription"), 0, True)
        products_column = gtk.TreeViewColumn(_("Installed Products"), \
                                             gtk.CellRendererProgress(), \
                                             value=1, text=2)
        self.subscription_view.append_column(products_column)

        add_column(_("Contract"), 3)
        add_column(_("Start Date"), 4)
        add_column(_("Expiration Date"), 5)

        self.update_subscriptions()

    def _pull_widgets(self, glade, names):
        for name in names:
            setattr(self, name, glade.get_widget(name))

    def update_subscriptions(self):
        entcerts = EntitlementDirectory().list()

        for cert in entcerts:
            order = cert.getOrder()

            subscription = []
            subscription.append(order.getName())

            products = cert.getProducts()
            installed = self._get_installed(products)

            subscription.append(self._calculate_percentage(installed, products))
            subscription.append('%s / %s' % (len(installed), len(products)))
            subscription.append(order.getContract())
            subscription.append(formatDate(order.getStart()))
            subscription.append(formatDate(order.getEnd()))
            subscription.append(cert.serialNumber())
            subscription.append(0.5)    # Center horizontally
            subscription.append(self._get_background_color(cert))

            self.subscription_store.append(subscription)

    def get_content(self):
        return self.content

    def get_label(self):
        return _("My Subscriptions")

    def update_details(self, treeselection):
        model, tree_iter = treeselection.get_selected()

        if tree_iter is None:
            return

        # Load the entitlement certificate for the selected row:
        serial = model.get_value(tree_iter, 6)
        cert = EntitlementDirectory().find(int(serial))
        order = cert.getOrder()
        products = [(product.getName(), product.getHash()) for product in cert.getProducts()]

        self.sub_details.show(order.getName(), 
                              contract=order.getContract() or "", 
                              start=str(formatDate(order.getStart())), 
                              end=str(formatDate(order.getEnd())),
                              products=products)

    def _get_background_color(self, entitlement_cert):
        date_range = entitlement_cert.validRange()

        # TODO:  Not sure if it is possible to have future-dated
        #        subscriptions here.  If so, this will need to change
        if not date_range.hasNow():
            return RED


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
