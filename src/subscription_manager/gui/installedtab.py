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
import os

from datetime import datetime

from rhsm.certificate import GMT

from subscription_manager.gui import widgets
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.certdirectory import ProductDirectory

from subscription_manager import managerlib, cert_sorter

import gettext
_ = gettext.gettext


class InstalledProductsTab(widgets.SubscriptionManagerTab):
    def __init__(self, backend, consumer, facts,
                 ent_dir=None, prod_dir=None):

        widgets = ['product_text', 'validity_text', 'subscription_text']
        super(InstalledProductsTab, self).__init__('installed.glade', widgets)

        self.product_dir = prod_dir or ProductDirectory()
        self.entitlement_dir = ent_dir or EntitlementDirectory()

        self.facts = facts
        self.cs = cert_sorter.CertSorter(prod_dir, ent_dir,
                                 facts_dict=self.facts.get_facts())

        #set up the iconset
        PARTIAL_IMG = os.path.join(os.path.dirname(__file__),
                                     "data/icons/partial.svg")
        VALID_IMG = os.path.join(os.path.dirname(__file__),
                                     "data/icons/valid.svg")
        INVALID_IMG = os.path.join(os.path.dirname(__file__),
                                     "data/icons/invalid.svg")
        self.iconset = {
            'green': gtk.gdk.pixbuf_new_from_file_at_size(VALID_IMG, 13, 13),
            'red': gtk.gdk.pixbuf_new_from_file_at_size(INVALID_IMG, 13, 13),
            'yellow': gtk.gdk.pixbuf_new_from_file_at_size(PARTIAL_IMG, 13, 13)
        }

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
        arch_col = self.add_text_column(_('Arch'), 'arch')
        arch_col.set_alignment(0.5)
        self.add_text_column(_('Status'), 'status')
        self.add_date_column(_('Start Date'), 'start_date')
        self.add_date_column(_('End Date'), 'expiration_date')

        self.update_products()

        # Monitor entitlements/products for additions/deletions
        def on_cert_change(filemonitor):
            self.update_products()

        backend.monitor_certs(on_cert_change)

    def update_products(self):
        self.store.clear()
        self.cs.refresh()

        for product_cert in self.product_dir.list():
            for product in product_cert.getProducts():
                product_hash = product.getHash()
                entitlement_cert = self.entitlement_dir. \
                                        findByProduct(product_hash)

                entry = {}
                entry['product'] = product.getName()
                entry['version'] = product.getVersion()
                entry['arch'] = product.getArch()
                # Common properties
                entry['align'] = 0.5

                if entitlement_cert:
                    order = entitlement_cert.getOrder()

                    entry['subscription'] = order.getName()
                    entry['start_date'] = self.cs.get_begin_date(product.getHash())
                    entry['expiration_date'] = self.cs.get_end_date(product.getHash())

                    # TODO:  Pull this date logic out into a separate lib!
                    #        This is also used in mysubstab...
                    date_range = entitlement_cert.validRange()
                    now = datetime.now(GMT())

                    if now < date_range.begin():
                        entry['status'] = _('Future Subscription')
                        entry['validity_note'] = _("Never Subscribed")
                    elif now > date_range.end():
                        entry['image'] = self._render_icon('red')
                        entry['status'] = _('Expired')
                        entry['validity_note'] = \
                            _('Subscription %s is expired' % order.getSubscription())
                    elif product.getHash() in self.cs.partially_valid_products:
                        entry['image'] = self._render_icon('yellow')
                        entry['status'] = _('Partially Subscribed')
                        entry['validity_note'] = _("Partially Subscribed")
                    else:
                        entry['image'] = self._render_icon('green')
                        entry['status'] = _('Subscribed')
                        entry['validity_note'] = \
                            _('Covered by contract %s through %s' % \
                            (order.getContract(),
                             managerlib.formatDate(entry['expiration_date'])))
                else:
                    entry['image'] = self._render_icon('red')
                    entry['status'] = _('Not Subscribed')
                    entry['validity_note'] = _("Not Subscribed")

                self.store.add_map(entry)

    def _render_icon(self, icon_id):
        try:
            return self.iconset[icon_id]
        except KeyError:
            print("Iconset does not contain icon for string '%s'" % icon_id)
            raise

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
