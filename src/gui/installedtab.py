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
import gio

from datetime import datetime

import widgets
from certlib import EntitlementDirectory, ProductDirectory
from certificate import GMT
from managerlib import formatDate

import gettext
_ = gettext.gettext
gettext.textdomain('subscription-manager')
gtk.glade.bindtextdomain('subscription-manager')

class InstalledProductsTab(widgets.SubscriptionManagerTab):

    def __init__(self, backend, consumer, facts):

        widgets = ['product_text', 'compliance_text', 'subscription_text']
        super(InstalledProductsTab, self).__init__('installed.glade', widgets)

        self.product_dir = ProductDirectory()
        self.entitlement_dir = EntitlementDirectory()

        # Product column
        text_renderer = gtk.CellRendererText()
        image_renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(_('Product'),
                                    image_renderer,
                                    pixbuf=self.store['image'])

        column.set_expand(True)
        column.pack_end(text_renderer, True)
        column.add_attribute(text_renderer, 'text', self.store['product'])
        column.add_attribute(text_renderer, 'cell-background',
                             self.store['background'])

        self.top_view.append_column(column)

        self.add_text_column(_('Version'), 'version')
        self.add_text_column(_('Compliance Status'), 'status')
        self.add_text_column(_('Contract'), 'contract')
        self.add_text_column(_('Start Date'), 'start_date')
        self.add_text_column(_('Expiration Date'), 'expiration_date')

        self.update_products()

        # Monitor products for additions/deletions
        def on_product_change(filemonitor, first_file, other_file, event_type):
            self.update_products()

        monitor = gio.File(self.product_dir.path).monitor()
        monitor.connect('changed', on_product_change)

    def update_products(self):
        self.store.clear()

        for product_cert in self.product_dir.list():
            for product in product_cert.getProducts():
                product_hash = product.getHash()
                entitlement_cert = self.entitlement_dir.findByProduct(product_hash)

                entry = {}
                entry['product'] = product.getName()
                entry['version'] = product.getVersion()
                # Common properties
                entry['align'] = 0.5

                if entitlement_cert:
                    order = entitlement_cert.getOrder()

                    entry['contract'] = order.getContract()
                    entry['subscription'] = order.getName()
                    entry['start_date'] = formatDate(order.getStart())
                    entry['expiration_date'] = formatDate(order.getEnd())

                    # TODO:  Pull this date logic out into a separate lib!
                    #        This is also used in mysubstab...
                    date_range = entitlement_cert.validRange()
                    now = datetime.now(GMT())

                    if now < date_range.begin():
                        entry['status'] = _('Future Subscription')
                        entry['compliance_note'] = _("Never Subscribed")
                    elif now > date_range.end():
                        entry['image'] = self._render_icon(gtk.STOCK_REMOVE)
                        entry['status'] = _('Out of Compliance')
                        entry['compliance_note'] = \
                            _('Subscription %s is expired' % order.getSubscription())
                    else:
                        entry['image'] = self._render_icon(gtk.STOCK_APPLY)
                        entry['status'] = _('In Compliance')
                        entry['compliance_note'] = \
                            _('Covered by contract %s through %s' % \
                            (order.getContract(), entry['expiration_date']))
                else:
                    entry['image'] = self._render_icon(gtk.STOCK_REMOVE)
                    entry['status'] = _('Out of Compliance')
                    entry['compliance_note'] = _("Never Subscribed")

                self.store.add_map(entry)

    def _render_icon(self, icon_id):
        return self.content.render_icon(icon_id, gtk.ICON_SIZE_MENU)

    def on_selection(self, selection):
        # Load the entitlement certificate for the selected row:
        product = selection['product']
        self.product_text.get_buffer().set_text(product)

        compliance = selection['compliance_note']
        self.compliance_text.get_buffer().set_text(compliance)

        subscription = selection['subscription'] or ''
        self.subscription_text.get_buffer().set_text(subscription)

    def get_type_map(self):
        return {
            'image': gtk.gdk.Pixbuf,
            'product': str,
            'version': str,
            'status': str,
            'compliance_note': str,
            'contract': str,
            'subscription': str,
            'start_date': str,
            'expiration_date': str,
            'serial': str,
            'align': float,
            'background': str
        }

    def get_label(self):
        return _('My Installed Software')

