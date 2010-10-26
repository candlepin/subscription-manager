
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
from managerlib import parse_date

import logutil
log = logutil.getLogger(__name__)

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/mysubs.glade")

class MySubscriptionsTab:

    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer

        glade = gtk.glade.XML(GLADE_XML)

        widget_names = ['subscription_view',
                        'content',
                        'subscription_text',
                        'start_date_text',
                        'expiration_date_text',
                        'contract_number_text']
        self._pull_widgets(glade, widget_names)

        self.subscription_view.get_selection().connect('changed', self.update_details)

        # Set up the model
        self.subscription_store = gtk.ListStore(str, float, str, str, str, str)
        self.subscription_view.set_model(self.subscription_store)

        text_renderer = gtk.CellRendererText()

        def add_column(name, column_number):
            column = gtk.TreeViewColumn(name, text_renderer, text=column_number)
            self.subscription_view.append_column(column)

        # Set up columns on the view
        add_column(_("Subscription"), 0)
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
            subscription.append(parse_date(order.getStart()))
            subscription.append(parse_date(order.getEnd()))

            self.subscription_store.append(subscription)

    def get_content(self):
        return self.content

    def get_label(self):
        return _("My Subscriptions")

    def update_details(self, treeselection):
        model, tree_iter = treeselection.get_selected()

        # TODO:  Do something about these magic numbers!
        sub = model.get_value(tree_iter, 0)
        contract = model.get_value(tree_iter, 2)
        start = model.get_value(tree_iter, 3)
        end = model.get_value(tree_iter, 4)

        self.subscription_text.get_buffer().set_text(sub)
        self.contract_number_text.get_buffer().set_text(contract)
        self.start_date_text.get_buffer().set_text(start)
        self.expiration_date_text.get_buffer().set_text(end)

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
