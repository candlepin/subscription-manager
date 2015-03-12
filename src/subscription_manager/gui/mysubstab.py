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

import gettext
import os
from datetime import datetime

import gobject
import gtk

from rhsm.certificate import GMT

from subscription_manager.async import AsyncBind
from subscription_manager.cert_sorter import EntitlementCertStackingGroupSorter
from subscription_manager import injection as inj

from subscription_manager.gui import messageWindow, progress
from subscription_manager.gui.storage import MappedTreeStore
from subscription_manager.gui import widgets
from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.utils import is_true_value


_ = gettext.gettext

prefix = os.path.dirname(__file__)
WARNING_IMG = os.path.join(prefix, "data/icons/partial.svg")
EXPIRING_IMG = os.path.join(prefix, "data/icons/expiring.svg")
EXPIRED_IMG = os.path.join(prefix, "data/icons/invalid.svg")


class MySubscriptionsTab(widgets.SubscriptionManagerTab):
    widget_names = widgets.SubscriptionManagerTab.widget_names + \
                    ['details_box', 'unsubscribe_button']
    gui_file = "mysubs.glade"

    def __init__(self, backend, parent_win,
                 ent_dir, prod_dir):
        """
        Create a new 'My Subscriptions' tab.
        """
        super(MySubscriptionsTab, self).__init__()
        self.backend = backend
        self.identity = inj.require(inj.IDENTITY)
        self.parent_win = parent_win
        self.entitlement_dir = ent_dir
        self.product_dir = prod_dir
        self.sub_details = widgets.ContractSubDetailsWidget(prod_dir)
        self.async_bind = AsyncBind(self.backend.certlib)
        self.pooltype_cache = inj.require(inj.POOLTYPE_CACHE)

        # Progress bar
        self.pb = None
        self.timer = 0

        # Put the details widget in the middle
        details = self.sub_details.get_widget()
        self.details_box.pack_start(details)

        # Set up columns on the view
        text_renderer = gtk.CellRendererText()
        image_renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(_('Subscription'))
        column.set_expand(True)
        column.pack_start(image_renderer, False)
        column.pack_start(text_renderer, False)
        column.add_attribute(image_renderer, 'pixbuf', self.store['image'])
        column.add_attribute(text_renderer, 'text', self.store['subscription'])
        column.add_attribute(text_renderer, 'cell-background',
                            self.store['background'])
        column.add_attribute(image_renderer, 'cell-background',
                            self.store['background'])
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)

        self.top_view.append_column(column)
        cols = []
        cols.append((column, 'text', 'subscription'))

        progress_renderer = gtk.CellRendererProgress()
        products_column = gtk.TreeViewColumn(_("Installed Products"),
                                             progress_renderer,
                                             value=self.store['installed_value'],
                                             text=self.store['installed_text'])
        products_column.add_attribute(progress_renderer, 'cell-background',
                            self.store['background'])
        self.empty_progress_renderer = gtk.CellRendererText()
        products_column.pack_end(self.empty_progress_renderer, True)
        products_column.set_cell_data_func(progress_renderer, self._update_progress_renderer)
        self.top_view.append_column(products_column)

        column = self.add_date_column(_("End Date"), 'expiration_date')
        cols.append((column, 'date', 'expiration_date'))

        column = self.add_text_column(_("Quantity"), 'quantity')
        cols.append((column, 'text', 'quantity'))

        self.set_sorts(self.store, cols)

        self.top_view.connect("row_activated",
                              widgets.expand_collapse_on_row_activated_callback)

        # Don't update the icon in the first run, we don't have real compliance data yet
        self.update_subscriptions(update_dbus=False)

        self.connect_signals({'on_unsubscribe_button_clicked': self.unsubscribe_button_clicked})

    def get_store(self):
        return MappedTreeStore(self.get_type_map())

    def _clear_progress_bar(self):
        if self.pb:
            self.pb.hide()
            gobject.source_remove(self.timer)
            self.timer = 0
            self.pb = None

    def _handle_unbind_exception(self, e, selection):
        self._clear_progress_bar()
        handle_gui_exception(e, _("There was an error removing %s with serial number %s") %
                (selection['subscription'], selection['serial']), self.parent_win, format_msg=False)

    def _unsubscribe_callback(self):
        self.backend.cs.force_cert_check()
        self._clear_progress_bar()

    def _on_unsubscribe_prompt_response(self, dialog, response, selection):
        if not response:
            return

        serial = long(selection['serial'])

        if self.identity.is_valid():
            self.pb = progress.Progress(_("Removing"),
                    _("Removing subscription. Please wait."))
            self.timer = gobject.timeout_add(100, self.pb.pulse)
            self.pb.set_parent_window(self.content.get_parent_window().get_user_data())
            self.async_bind.unbind(serial, selection, self._unsubscribe_callback, self._handle_unbind_exception)
        else:
            # unregistered, just delete the certs directly
            self.backend.entcertlib.delete([serial])
            self.backend.cs.force_cert_check()

    def unsubscribe_button_clicked(self, widget):
        selection = widgets.SelectionWrapper(self.top_view.get_selection(), self.store)

        # nothing selected
        if not selection.is_valid():
            return

        # remove all markup, see rh bz#982286
        subscription_text = gobject.markup_escape_text(selection['subscription'])

        prompt = messageWindow.YesNoDialog(_("Are you sure you want to remove %s?") % subscription_text,
                self.content.get_toplevel())
        prompt.connect('response', self._on_unsubscribe_prompt_response, selection)

    def update_subscriptions(self, update_dbus=True):
        """
        Pulls the entitlement certificates and updates the subscription model.
        """
        self.pooltype_cache.update()
        sorter = EntitlementCertStackingGroupSorter(self.entitlement_dir.list())
        self.store.clear()
        for group in sorter.groups:
            self._add_group(group)
        self.top_view.expand_all()
        self._stripe_rows(None, self.store)
        if update_dbus:
            inj.require(inj.DBUS_IFACE).update()
        self.unsubscribe_button.set_property('sensitive', False)
        # 841396: Select first item in My Subscriptions table by default
        selection = self.top_view.get_selection()
        selection.select_path(0)

    def _add_group(self, group):
        tree_iter = None
        if group.name and len(group.entitlements) > 1:
            unique = self.find_unique_name_count(group.entitlements)
            if unique - 1 > 1:
                name_string = _("Stack of %s and %s others") % \
                        (group.name, str(unique - 1))
            elif unique - 1 == 1:
                name_string = _("Stack of %s and 1 other") % (group.name)
            else:
                name_string = _("Stack of %s") % (group.name)
            tree_iter = self.store.add_map(tree_iter, self._create_stacking_header_entry(name_string))

        new_parent_image = None
        for i, cert in enumerate(group.entitlements):
            image = self._get_entry_image(cert)
            self.store.add_map(tree_iter, self._create_entry_map(cert, image))

            # Determine if we need to change the parent's image. We
            # will match the parent's image with the children if any of
            # the children have an image.
            if self.image_ranks_higher(new_parent_image, image):
                new_parent_image = image

        # Update the parent image if required.
        if new_parent_image and tree_iter:
            self.store.set_value(tree_iter, self.store['image'],
                    gtk.gdk.pixbuf_new_from_file_at_size(new_parent_image, 13, 13))

    def find_unique_name_count(self, entitlements):
        result = dict()
        for ent in entitlements:
            result[ent.order.name] = ent.order.name
        return len(result)

    def image_ranks_higher(self, old_image, new_image):
        images = [None, WARNING_IMG, EXPIRING_IMG, EXPIRED_IMG]
        return images.index(new_image) > images.index(old_image)

    def get_label(self):
        return _("My Subscriptions")

    def get_type_map(self):
        return {
            'image': gtk.gdk.Pixbuf,
            'subscription': str,
            'installed_value': float,
            'installed_text': str,
            'start_date': gobject.TYPE_PYOBJECT,
            'expiration_date': gobject.TYPE_PYOBJECT,
            'quantity': str,
            'serial': str,
            'align': float,
            'background': str,
            'is_group_row': bool
        }

    def on_selection(self, selection):
        """
        Updates the 'Subscription Details' panel with the currently selected
        subscription.
        """

        if selection['is_group_row']:
            self.sub_details.clear()
            self.unsubscribe_button.set_property('sensitive', False)
            return

        self.unsubscribe_button.set_property('sensitive', True)
        # Load the entitlement certificate for the selected row:
        serial = selection['serial']
        cert = self.entitlement_dir.find(long(serial))
        order = cert.order
        products = [(product.name, product.id)
                        for product in cert.products]

        reasons = []
        if self.backend.cs.are_reasons_supported():
            reasons = self.backend.cs.reasons.get_subscription_reasons(cert.subject['CN'])
            if not reasons:
                if cert in self.backend.cs.valid_entitlement_certs:
                    reasons.append(_('Subscription is current.'))
                else:
                    if cert.valid_range.end() < datetime.now(GMT()):
                        reasons.append(_('Subscription is expired.'))
                    else:
                        reasons.append(_('Subscription has not begun.'))
        else:
            reasons.append(_("Subscription management service doesn't support Status Details."))

        pool_type = ''
        if cert.pool and cert.pool.id:
            pool_type = self.pooltype_cache.get(cert.pool.id)

        if is_true_value(order.virt_only):
            virt_only = _("Virtual")
        else:
            virt_only = _("Physical")

        if is_true_value(order.provides_management):
            management = _("Yes")
        else:
            management = _("No")

        self.sub_details.show(order.name,
                              contract=order.contract or "",
                              start=cert.valid_range.begin(),
                              end=cert.valid_range.end(),
                              account=order.account or "",
                              management=management,
                              virt_only=virt_only or "",
                              support_level=order.service_level or "",
                              support_type=order.service_type or "",
                              products=products,
                              sku=order.sku,
                              reasons=reasons,
                              expiring=cert.is_expiring(),
                              pool_type=pool_type)

    def on_no_selection(self):
        """
        Clears out the subscription details panel when no subscription is
        selected and disables the unsubscribe button.
        """
        self.sub_details.clear()
        self.unsubscribe_button.set_property('sensitive', False)

    def _create_stacking_header_entry(self, title):
        entry = {}
        entry['subscription'] = title
        entry['installed_value'] = 0.0
        entry['align'] = 0.5         # Center horizontally
        entry['background'] = None
        entry['is_group_row'] = True

        return entry

    def _create_entry_map(self, cert, image):
        order = cert.order
        products = cert.products
        installed = self._get_installed(products)

        # Initialize an entry list of the proper length
        entry = {}
        if image:
            entry['image'] = gtk.gdk.pixbuf_new_from_file_at_size(image, 13, 13)
        entry['subscription'] = order.name
        entry['installed_value'] = self._percentage(installed, products)
        entry['installed_text'] = '%s / %s' % (len(installed), len(products))
        entry['start_date'] = cert.valid_range.begin()
        entry['expiration_date'] = cert.valid_range.end()
        entry['quantity'] = str(order.quantity_used)
        entry['serial'] = str(cert.serial)
        entry['align'] = 0.5         # Center horizontally
        entry['background'] = None
        entry['is_group_row'] = False

        return entry

    def _get_entry_image(self, cert):
        date_range = cert.valid_range
        now = datetime.now(GMT())

        if date_range.end() < now:
            return EXPIRED_IMG

        if cert.is_expiring():
            return EXPIRING_IMG

        if cert.subject and 'CN' in cert.subject and \
                self.backend.cs.reasons.get_subscription_reasons(cert.subject['CN']):
            return WARNING_IMG

        return None

    def _percentage(self, subset, full_set):
        if (len(full_set) == 0):
            return 100
        else:
            return (float(len(subset)) / len(full_set)) * 100

    def _get_installed(self, products):
        installed_dir = self.product_dir
        installed_products = []

        for product in products:
            installed = installed_dir.find_by_product(product.id)

            if installed:
                installed_products.append(installed)

        return installed_products

    def _update_progress_renderer(self, column, cell_renderer, tree_model, tree_iter, data=None):
        hide_progress = tree_model.get_value(tree_iter, self.store['is_group_row'])
        background_color = tree_model.get_value(tree_iter, self.store['background'])

        cell_renderer.set_property('visible', not hide_progress)

        self.empty_progress_renderer.set_property('visible', hide_progress)
        self.empty_progress_renderer.set_property('cell-background', background_color)
