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

WARNING_DAYS = 6 * 7   # 6 weeks * 7 days / week

class MySubscriptionsTab(widgets.SubscriptionManagerTab):

    def __init__(self, backend, consumer, facts):
        """
        Create a new 'My Subscriptions' tab.
        """
        super(MySubscriptionsTab, self).__init__('mysubs.glade')
        
        self.sub_details = widgets.SubDetailsWidget()

        # Put the details widget in the middle
        details = self.sub_details.get_widget()
        self.content.add(details)
            
        # Set up columns on the view
        self.add_text_column(_("Subscription"), 'subscription', True)
        products_column = gtk.TreeViewColumn(_("Installed Products"),
                                             gtk.CellRendererProgress(),
                                             value=self.store['installed_value'],
                                             text=self.store['installed_text'])
        self.top_view.append_column(products_column)

        self.add_text_column(_("Contract"), 'contract')
        self.add_text_column(_("Start Date"), 'start_date')
        self.add_text_column(_("Expiration Date"), 'expiration_date')

        self.update_subscriptions()

    def update_subscriptions(self):
        """
        Pulls the entitlement certificates and updates the subscription model.
        """

        for cert in EntitlementDirectory().list():
            entry = self._create_entry_map(cert)   
            self.store.add_map(entry)

    def get_label(self):
        return _("My Subscriptions")
        
    def get_type_map(self):
        return {
            'subscription': str,
            'installed_value': float,
            'installed_text': str,
            'contract': str,
            'start_date': str,
            'expiration_date': str,
            'serial': str,
            'align': float,
            'background': str
        }

    def on_selection(self, selection):
        """
        Updates the 'Subscription Details' panel with the currently selected
        subscription.
        """
        # Load the entitlement certificate for the selected row:
        serial = selection['serial']
        cert = EntitlementDirectory().find(int(serial))
        order = cert.getOrder()
        products = [(product.getName(), product.getHash())
                        for product in cert.getProducts()]

        self.sub_details.show(order.getName(), 
                              contract=order.getContract() or "", 
                              start=str(formatDate(order.getStart())), 
                              end=str(formatDate(order.getEnd())),
                              account=order.getAccountNumber() or "",
                              products=products)
                              
    def _create_entry_map(self, cert):
        order = cert.getOrder()
        products = cert.getProducts()
        installed = self._get_installed(products)

        # Initialize an entry list of the proper length
        entry = {}
        entry['subscription'] = order.getName()
        entry['installed_value'] = self._percentage(installed, products)
        entry['installed_text'] = '%s / %s' % (len(installed), len(products))
        entry['contract'] = order.getContract()
        entry['start_date'] = formatDate(order.getStart())
        entry['expiration_date'] = formatDate(order.getEnd())
        entry['serial'] = cert.serialNumber()
        entry['align'] = 0.5         # Center horizontally
        entry['background'] = self._get_background_color(cert)
        
        return entry

    def _get_background_color(self, entitlement_cert):
        date_range = entitlement_cert.validRange()
        now = datetime.now(GMT())

        if date_range.end() < now:
            return RED

        if date_range.end() - timedelta(days=WARNING_DAYS) < now:
            return YELLOW

    def _percentage(self, subset, full_set):
        return (float(len(subset)) / len(full_set)) * 100

    def _get_installed(self, products):
        installed_dir = ProductDirectory()
        installed_products = []

        for product in products:
            installed = installed_dir.findByProduct(product.getHash())

            if installed:
                installed_products.append(installed)

        return installed_products
