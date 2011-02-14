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
from certlib import EntitlementDirectory, ProductDirectory, CertLib
from rhsm.certificate import GMT

import messageWindow
import widgets
from utils import handle_gui_exception

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
        super(MySubscriptionsTab, self).__init__('mysubs.glade', ['details_box'])
        self.backend = backend
        self.consumer = consumer
        self.facts = facts

        self.sub_details = widgets.SubDetailsWidget()

        # Put the details widget in the middle
        details = self.sub_details.get_widget()
        self.details_box.pack_start(details)

        # Set up columns on the view
        self.add_text_column(_("Subscription"), 'subscription', True)
        products_column = gtk.TreeViewColumn(_("Installed Products"),
                                             gtk.CellRendererProgress(),
                                             value=self.store['installed_value'],
                                             text=self.store['installed_text'])
        self.top_view.append_column(products_column)

        self.add_date_column(_("End Date"), 'expiration_date')

        self.update_subscriptions()

        self.unsubscribe_button = self.glade.get_widget('unsubscribe_button')
        self.glade.signal_autoconnect({'on_unsubscribe_button_clicked': self.unsubscribe_button_clicked})

        # Monitor entitlements/products for additions/deletions
        def on_cert_change(filemonitor, first_file, other_file, event_type):
            self.update_subscriptions()

        backend.monitor_certs(on_cert_change)

    def _on_unsubscribe_prompt_response(self, dialog, response, selection):
        if not response:
            return

        serial = selection['serial']
        try:
            self.backend.uep.unbindBySerial(self.consumer.uuid, serial)
        except Exception, e:
            handle_gui_exception(e, _("There was an error unsubsribing from %s with serial number %s" % (selection['subscription'],serial)))

        self.backend.certlib.update()
        self.update_subscriptions()

    def unsubscribe_button_clicked(self, widget):
        selection = widgets.SelectionWrapper(self.top_view.get_selection(), self.store)

        # nothing selected
        if not selection.is_valid():
            return

        prompt = messageWindow.YesNoDialog(_("Are you sure you want to unsubscribe from %s?" % selection['subscription']),
                self.content.get_toplevel())
        prompt.connect('response', self._on_unsubscribe_prompt_response, selection)

    def update_subscriptions(self):
        """
        Pulls the entitlement certificates and updates the subscription model.
        """
        self.store.clear()

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

        if str(order.getProvidesManagement()) == "1":
            management = _("Yes")
        else:
            management = _("No")

        self.sub_details.show(order.getName(),
                              contract=order.getContract() or "",
                              start=order.getStart(),
                              end=order.getEnd(),
                              account=order.getAccountNumber() or "",
                              management=management,
                              support_level=order.getSupportLevel() or "",
                              support_type=order.getSupportType() or "",
                              products=products)

    def on_no_selection(self):
        """
        Clears out the subscription details panel when no subscription is
        selected.
        """
        self.sub_details.clear()

    def _create_entry_map(self, cert):
        order = cert.getOrder()
        products = cert.getProducts()
        installed = self._get_installed(products)

        # Initialize an entry list of the proper length
        entry = {}
        entry['subscription'] = order.getName()
        entry['installed_value'] = self._percentage(installed, products)
        entry['installed_text'] = '%s / %s' % (len(installed), len(products))
        entry['start_date'] = order.getStart()
        entry['expiration_date'] = order.getEnd()
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
        if (len(full_set) == 0):
            return 100
        else:
            return (float(len(subset)) / len(full_set)) * 100

    def _get_installed(self, products):
        installed_dir = ProductDirectory()
        installed_products = []

        for product in products:
            installed = installed_dir.findByProduct(product.getHash())

            if installed:
                installed_products.append(installed)

        return installed_products

