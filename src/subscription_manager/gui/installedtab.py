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
import gobject

from datetime import datetime

from rhsm.certificate import GMT

from subscription_manager.gui import widgets
from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory

from subscription_manager import managerlib

import gettext
_ = gettext.gettext


class InstalledProductsTab(widgets.SubscriptionManagerTab):
    def __init__(self, backend, consumer, facts,
                 ent_dir=None, prod_dir=None):

        widgets = ['product_text', 'validity_text', 'subscription_text']
        super(InstalledProductsTab, self).__init__('installed.glade', widgets)

        self.product_dir = prod_dir or ProductDirectory()
        self.entitlement_dir = ent_dir or EntitlementDirectory()

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
        self.add_text_column(_('Arch'), 'arch')
        self.add_text_column(_('Certificate'), 'status')
        self.add_date_column(_('Start Date'), 'start_date')
        self.add_date_column(_('End Date'), 'expiration_date')

        self.update_products()

        # Monitor entitlements/products for additions/deletions
        def on_cert_change(filemonitor):
            self.update_products()

        backend.monitor_certs(on_cert_change)

    def update_products(self):
        self.store.clear()

        for product_cert in self.product_dir.list():
            for product in product_cert.getProducts():
                product_hash = product.getHash()
                entitlement_cert = self.entitlement_dir.findByProduct(product_hash)

                entry = {}
                entry['product'] = product.getName()
                entry['version'] = product.getVersion()
                entry['arch'] = product.getArch()
                # Common properties
                entry['align'] = 0.5

                if entitlement_cert:
                    order = entitlement_cert.getOrder()

                    entry['subscription'] = order.getName()
                    entry['start_date'] = entitlement_cert.validRange().begin()
                    entry['expiration_date'] = entitlement_cert.validRange().end()

                    # TODO:  Pull this date logic out into a separate lib!
                    #        This is also used in mysubstab...
                    date_range = entitlement_cert.validRange()
                    now = datetime.now(GMT())

                    if now < date_range.begin():
                        entry['status'] = _('Future Subscription')
                        entry['validity_note'] = _("Never Subscribed")
                    elif now > date_range.end():
                        entry['image'] = self._render_icon(gtk.STOCK_NO)
                        entry['status'] = _('Invalid')
                        entry['validity_note'] = \
                            _('Subscription %s is expired' % order.getSubscription())
                    else:
                        entry['image'] = self._render_icon(gtk.STOCK_YES)
                        entry['status'] = _('Valid')
                        entry['validity_note'] = \
                            _('Covered by contract %s through %s' % \
                            (order.getContract(),
                             managerlib.formatDate(entry['expiration_date'])))
                else:
                    entry['image'] = self._render_icon(gtk.STOCK_NO)
                    entry['status'] = _('Missing')
                    entry['validity_note'] = _("Never Subscribed")

                self.store.add_map(entry)

    def _render_icon(self, icon_id):
        return self.content.render_icon(icon_id, gtk.ICON_SIZE_MENU)

    def on_selection(self, selection):
        # Load the entitlement certificate for the selected row:
        product = selection['product']
        self.product_text.get_buffer().set_text(product)

        validity = selection['validity_note']
        self.validity_text.get_buffer().set_text(validity)

        subscription = selection['subscription'] or ''
        self.subscription_text.get_buffer().set_text(subscription)

    def on_no_selection(self):
        self.product_text.get_buffer().set_text("")
        self.validity_text.get_buffer().set_text("")
        self.subscription_text.get_buffer().set_text("")

    def get_type_map(self):
        return {
            'image': gtk.gdk.Pixbuf,
            'product': str,
            'version': str,
            'arch': str,
            'status': str,
            'validity_note': str,
            'subscription': str,
            'start_date': gobject.TYPE_PYOBJECT,
            'expiration_date': gobject.TYPE_PYOBJECT,
            'serial': str,
            'align': float,
            'background': str
        }

    def get_label(self):
        return _('My Installed Software')
