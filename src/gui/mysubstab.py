
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

from xml.utils.iso8601 import parse
from certlib import EntitlementDirectory, ProductDirectory

import logutil
log = logutil.getLogger(__name__)

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/mysubs.glade")

class MySubscriptionsTab:

    def __init__(self, backend, consumer):
        self.backend = backend
        self.consumer = consumer

        glade = gtk.glade.XML(GLADE_XML)
        self.subscription_view = glade.get_widget("subscription_view")
        self.content = glade.get_widget("content")

        # Set up the model
        self.subscription_store = gtk.ListStore(str, str, str, str, str)
        self.subscription_view.set_model(self.subscription_store)

        text_renderer = gtk.CellRendererText()

        def add_column(name):
            column_number = len(self.subscription_view.get_columns())
            column = gtk.TreeViewColumn(name, text_renderer, text=column_number)

            self.subscription_view.append_column(column)

        # Set up columns on the view
        add_column(_("Subscription"))
        add_column(_("Installed Products"))
        add_column(_("Contract"))
        add_column(_("Start Date"))
        add_column(_("Expiration Date"))

        self.update_subscriptions()

    def update_subscriptions(self):
        entcerts = EntitlementDirectory().list()
        for cert in entcerts:
            order = cert.getOrder()

            subscription = []
            subscription.append(order.getName())

            products = cert.getProducts()
            installed = self._get_installed(products)

            subscription.append('%s/%s' % (len(installed), len(products)))
            subscription.append(order.getContract())
            subscription.append(self._parse_date(order.getStart()))
            subscription.append(self._parse_date(order.getEnd()))

            self.subscription_store.append(subscription)

    def get_content(self):
        return self.content

    def get_label(self):
        return _("My Subscriptions")

    def _parse_date(self, date_string):
        try:
            return datetime.date.fromtimestamp(parse(date_string))
        except:
            return None

    def _get_installed(self, products):
        installed_dir = ProductDirectory()
        installed_products = []

        for product in products:
            installed = installed_dir.findByProduct(product.getHash())

            if installed:
                installed_products.append(installed)

        return installed_products
