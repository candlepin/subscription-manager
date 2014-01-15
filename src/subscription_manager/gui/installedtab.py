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
from subscription_manager.hwprobe import ClassicCheck
from subscription_manager.cert_sorter import CertSorter, FUTURE_SUBSCRIBED, SUBSCRIBED, NOT_SUBSCRIBED, EXPIRED, PARTIALLY_SUBSCRIBED

from subscription_manager import managerlib, cert_sorter
from subscription_manager.validity import find_first_invalid_date

import gettext
_ = gettext.gettext


prefix = os.path.dirname(__file__)
VALID_IMG = os.path.join(prefix, "data/icons/valid.svg")
PARTIAL_IMG = os.path.join(prefix, "data/icons/partial.svg")
INVALID_IMG = os.path.join(prefix, "data/icons/invalid.svg")

ICONSET = {
    'green': gtk.gdk.pixbuf_new_from_file_at_size(VALID_IMG, 13, 13),
    'red': gtk.gdk.pixbuf_new_from_file_at_size(INVALID_IMG, 13, 13),
    'yellow': gtk.gdk.pixbuf_new_from_file_at_size(PARTIAL_IMG, 13, 13)
}


PARTIAL = 0
INVALID = 1
VALID = 2


class InstalledProductsTab(widgets.SubscriptionManagerTab):
    def __init__(self, backend, consumer, facts, tab_icon,
                 parent, ent_dir=None, prod_dir=None):

        widgets = ['product_text', 'validity_text', 'subscription_text',
                 'subscription_status_label',
                 'update_certificates_button']
        super(InstalledProductsTab, self).__init__('installed.glade', widgets)

        self.tab_icon = tab_icon

        self.product_dir = prod_dir or ProductDirectory()
        self.entitlement_dir = ent_dir or EntitlementDirectory()

        self.facts = facts
        self.cs = cert_sorter.CertSorter(prod_dir, ent_dir,
                self.facts.get_facts())

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

        self.glade.signal_autoconnect({
            "on_update_certificates_button_clicked":
            parent._update_certificates_button_clicked,
        })

        self.update_products()

        # Monitor entitlements/products for additions/deletions
        def on_cert_change(filemonitor):
            self.update_products()
            self._set_validity_status()

        backend.monitor_certs(on_cert_change)

    def update_products(self):
        self.store.clear()
        self.cs = cert_sorter.CertSorter(self.product_dir,
                self.entitlement_dir, self.facts.get_facts())
        for product_cert in self.product_dir.list():
            for product in product_cert.getProducts():
                product_hash = product.getHash()
                status = self.cs.get_status(product_hash)

                entry = {}
                entry['product'] = product.getName()
                entry['version'] = product.getVersion()
                entry['arch'] = product.getArch()
                # Common properties
                entry['align'] = 0.5

                # TODO:  Pull this date logic out into a separate lib!
                #        This is also used in mysubstab...
                if status != NOT_SUBSCRIBED:
                    # TODO: Simplified and will need adjustment when the
                    # date range work is done. Shows all available contracts for
                    # the product and shows the final end date.
                    entitlement_cert = self.entitlement_dir.findByProduct(product_hash)
                    contract = ""
                    name = ""
                    first = True
                    for cert in self.entitlement_dir.listValid():
                        if entitlement_cert.getOrder().getStackingId() == "" or \
                            cert.getOrder().getStackingId() == \
                            entitlement_cert.getOrder().getStackingId():
                            if not first:
                                contract += ", "
                                name += ", "
                            first = False
                            contract = contract + cert.getOrder().getContract()
                            name = name + cert.getOrder().getName()

                    entry['subscription'] = name
                    entry['start_date'] = self.cs.get_begin_date(product.getHash())
                    entry['expiration_date'] = self.cs.get_end_date(product.getHash())

                    if status == FUTURE_SUBSCRIBED:
                        entry['image'] = self._render_icon('red')
                        entry['status'] = _('Future Subscription')
                        entry['validity_note'] = _("Never Subscribed")
                    elif status == EXPIRED:
                        #TODO: This order value may potentially be wrong in the case of
                        # multi-entitlement.
                        order = entitlement_cert.getOrder()
                        entry['image'] = self._render_icon('red')
                        entry['status'] = _('Expired')
                        entry['validity_note'] = \
                            _('Subscription %s is expired') % order.getSubscription()
                    elif status == PARTIALLY_SUBSCRIBED:
                        entry['image'] = self._render_icon('yellow')
                        entry['status'] = _('Partially Subscribed')
                        entry['validity_note'] = _("Partially Subscribed")
                    else:
                        entry['image'] = self._render_icon('green')
                        entry['status'] = _('Subscribed')
                        entry['validity_note'] = \
                            _('Covered by contract %s through %s') % \
                            (contract,
                             managerlib.formatDate(entry['expiration_date']))
                else:
                    entry['image'] = self._render_icon('red')
                    entry['status'] = _('Not Subscribed')
                    entry['validity_note'] = _("Not Subscribed")

                self.store.add_map(entry)

    def _render_icon(self, icon_id):
        try:
            return ICONSET[icon_id]
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

    def _set_status_icons(self, status_type):
        img = INVALID_IMG
        if status_type == PARTIAL:
            img = PARTIAL_IMG
        elif status_type == VALID:
            img = VALID_IMG

        pix_buf = gtk.gdk.pixbuf_new_from_file_at_size(img, 13, 13)
        self.tab_icon.set_from_pixbuf(pix_buf)

    def _set_validity_status(self):
        """ Updates the entitlement validity status portion of the UI. """

        if ClassicCheck().is_registered_with_classic():
            self._set_status_icons(VALID)
            self.subscription_status_label.set_text(
                _("This system is registered to RHN Classic"))
            return

        # Look for products which have invalid entitlements
        sorter = CertSorter(self.product_dir, self.entitlement_dir,
                self.facts.get_facts())

        warn_count = len(sorter.expired_products) + \
                len(sorter.unentitled_products)

        partial_count = len(sorter.partially_valid_products)

        self.update_certificates_button.show()
        if warn_count > 0:
            self._set_status_icons(INVALID)
            # Change wording slightly for just one product
            if warn_count > 1:
                self.subscription_status_label.set_markup(
                        _("You have <b>%s</b> products with <i>invalid</i> entitlement certificates.")
                        % warn_count)
            else:
                self.subscription_status_label.set_markup(
                        _("You have <b>1</b> product with an <i>invalid</i> entitlement certificate."))

        elif partial_count > 0:
            self._set_status_icons(PARTIAL)
            # Change wording slightly for just one product
            if partial_count > 1:
                self.subscription_status_label.set_markup(
                        _("You have <b>%s</b> products in need of <i>additional</i> entitlement certificates.")
                        % partial_count)
            else:
                self.subscription_status_label.set_markup(
                        _("You have <b>1</b> product in need of <i>additional</i> entitlement certificates."))

        else:
            first_invalid = find_first_invalid_date(self.entitlement_dir,
                    self.product_dir, self.facts.get_facts())
            self._set_status_icons(VALID)
            if first_invalid:
                self.subscription_status_label.set_markup(
                        _("Product entitlement certificates <i>valid</i> until %s") % \
                            managerlib.formatDate(first_invalid))
            else:
                # No product certs installed, no first invalid date, and
                # the subscription assistant can't do anything, so we'll disable
                # the button to launch it:
                self.subscription_status_label.set_text(
                        _("No product certificates installed."))
                self.update_certificates_button.hide()

    def set_registered(self, is_registered):
        self.update_certificates_button.set_sensitive(is_registered)

    def refresh(self):
        self._set_next_update()
        self._set_validity_status()
