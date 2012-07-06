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
from datetime import datetime, timedelta

from rhsm.certificate import GMT

from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory
from subscription_manager.certlib import Disconnected
from subscription_manager.gui import messageWindow
from subscription_manager.gui import widgets
from subscription_manager.gui.utils import handle_gui_exception, get_dbus_iface,\
    get_cell_background_color

import gettext
from subscription_manager.cert_sorter import EntitlementCertStackingGroupSorter
from subscription_manager.gui.storage import MappedTreeStore
_ = gettext.gettext

WARNING_DAYS = 6 * 7   # 6 weeks * 7 days / week

WARNING_COLOR = '#FFFB82'
EXPIRED_COLOR = '#FFAF99'


class MySubscriptionsTab(widgets.SubscriptionManagerTab):

    # Are facts required here? [mstead]
    def __init__(self, backend, consumer, facts, parent_win,
                 ent_dir=None,
                 prod_dir=None):
        """
        Create a new 'My Subscriptions' tab.
        """
        super(MySubscriptionsTab, self).__init__('mysubs.glade', ['details_box',
                                                                  'unsubscribe_button'])
        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.parent_win = parent_win
        self.entitlement_dir = ent_dir or EntitlementDirectory()
        self.product_dir = prod_dir or ProductDirectory()

        self.sub_details = widgets.SubDetailsWidget()

        # Put the details widget in the middle
        details = self.sub_details.get_widget()
        self.details_box.pack_start(details)

        # Set up columns on the view
        column = self.add_text_column(_("Subscription"), 'subscription', True)
        cols = []
        cols.append((column, 'text', 'subscription'))

        progress_renderer = gtk.CellRendererProgress()
        products_column = gtk.TreeViewColumn(_("Installed Products"),
                                             progress_renderer,
                                             value=self.store['installed_value'],
                                             text=self.store['installed_text'])
        self.empty_progress_renderer = gtk.CellRendererText()
        products_column.pack_end(self.empty_progress_renderer, True)
        products_column.set_cell_data_func(progress_renderer, self._update_progress_renderer)
        self.top_view.append_column(products_column)

        column = self.add_date_column(_("End Date"), 'expiration_date')
        cols.append((column, 'date', 'expiration_date'))

        # Disable row striping on the tree view as we are overriding the behavior
        # to display stacking groups as one color.
        self.top_view.set_rules_hint(False)

        column = self.add_text_column(_("Quantity"), 'quantity')
        cols.append((column, 'text', 'quantity'))

        self.set_sorts(cols)

        self.top_view.connect("row_activated",
                              widgets.expand_collapse_on_row_activated_callback)

        self.update_subscriptions()

        self.glade.signal_autoconnect({'on_unsubscribe_button_clicked': self.unsubscribe_button_clicked})

        # Monitor entitlements/products for additions/deletions
        def on_cert_change(filemonitor):
            self.update_subscriptions()

        self.backend.monitor_certs(on_cert_change)

    def get_store(self):
        return MappedTreeStore(self.get_type_map())

    def _on_unsubscribe_prompt_response(self, dialog, response, selection):
        if not response:
            return

        serial = long(selection['serial'])

        if self.backend.is_registered():
            try:
                self.backend.uep.unbindBySerial(self.consumer.uuid, serial)
            except Exception, e:
                handle_gui_exception(e, _("There was an error unsubscribing from %s with serial number %s") % (selection['subscription'], serial), self.parent_win, formatMsg=False)

            try:
                self.backend.certlib.update()
            except Disconnected, e:
                pass
        else:
            # unregistered, just delete the certs directly
            self.backend.certlib.delete([serial])

        self.update_subscriptions()

    def unsubscribe_button_clicked(self, widget):
        selection = widgets.SelectionWrapper(self.top_view.get_selection(), self.store)

        # nothing selected
        if not selection.is_valid():
            return

        prompt = messageWindow.YesNoDialog(_("Are you sure you want to unsubscribe from %s?") % selection['subscription'],
                self.content.get_toplevel())
        prompt.connect('response', self._on_unsubscribe_prompt_response, selection)

    def update_subscriptions(self):
        """
        Pulls the entitlement certificates and updates the subscription model.
        """
        self.store.clear()
        sorter = EntitlementCertStackingGroupSorter(self.entitlement_dir.list())
        for idx, group in enumerate(sorter.groups):
            self._add_group(idx, group)
        self.top_view.expand_all()
        dbus_iface = get_dbus_iface()
        dbus_iface.check_status(ignore_reply=True)
        self.facts.refresh_validity_facts()
        self.unsubscribe_button.set_property('sensitive', False)

    def _add_group(self, group_idx, group):
        iter = None
        if group.name:
            bg_color = self._get_background_color(group_idx)
            iter = self.store.add_map(iter, self._create_stacking_header_entry(group.name,
                                                                               bg_color))
        change_parent_color = False
        new_parent_color = None
        for i, cert in enumerate(group.entitlements):
            bg_color = self._get_background_color(group_idx, cert)
            self.store.add_map(iter, self._create_entry_map(cert, bg_color))

            # Determine if we need to change the parent's color. We
            # will match the parent's color with the childrent if all
            # children are the same color.
            if i == 0:
                new_parent_color = bg_color
            else:
                change_parent_color = new_parent_color == bg_color

        # Update the parent color if required.
        if change_parent_color and iter:
            self.store.set_value(iter, self.store['background'], new_parent_color)

    def get_label(self):
        return _("My Subscriptions")

    def get_type_map(self):
        return {
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
        order = cert.getOrder()
        products = [(product.getName(), product.getHash())
                        for product in cert.getProducts()]

        if str(order.getVirtOnly()) == "1":
            virt_only = _("Virtual")
        else:
            virt_only = _("Physical")

        if str(order.getProvidesManagement()) == "1":
            management = _("Yes")
        else:
            management = _("No")

        self.sub_details.show(order.getName(),
                              contract=order.getContract() or "",
                              start=cert.validRange().begin(),
                              end=cert.validRange().end(),
                              account=order.getAccountNumber() or "",
                              management=management,
                              virt_only=virt_only or "",
                              support_level=order.getSupportLevel() or "",
                              support_type=order.getSupportType() or "",
                              products=products,
                              sku=order.getSku())

    def on_no_selection(self):
        """
        Clears out the subscription details panel when no subscription is
        selected.
        """
        self.sub_details.clear()

    def _create_stacking_header_entry(self, title, background_color):
        entry = {}
        entry['subscription'] = title
        entry['installed_value'] = 0.0
        entry['align'] = 0.5         # Center horizontally
        entry['background'] = background_color
        entry['is_group_row'] = True

        return entry

    def _create_entry_map(self, cert, background_color):
        order = cert.getOrder()
        products = cert.getProducts()
        installed = self._get_installed(products)

        # Initialize an entry list of the proper length
        entry = {}
        entry['subscription'] = order.getName()
        entry['installed_value'] = self._percentage(installed, products)
        entry['installed_text'] = '%s / %s' % (len(installed), len(products))
        entry['start_date'] = cert.validRange().begin()
        entry['expiration_date'] = cert.validRange().end()
        entry['quantity'] = order.getQuantityUsed()
        entry['serial'] = cert.serialNumber()
        entry['align'] = 0.5         # Center horizontally
        entry['background'] = background_color
        entry['is_group_row'] = False

        return entry

    def _get_background_color(self, idx, entitlement_cert=None):
        if entitlement_cert:
            date_range = entitlement_cert.validRange()
            now = datetime.now(GMT())

            if date_range.end() < now:
                return EXPIRED_COLOR

            if date_range.end() - timedelta(days=WARNING_DAYS) < now:
                return WARNING_COLOR

        return get_cell_background_color(idx)

    def _percentage(self, subset, full_set):
        if (len(full_set) == 0):
            return 100
        else:
            return (float(len(subset)) / len(full_set)) * 100

    def _get_installed(self, products):
        installed_dir = self.product_dir
        installed_products = []

        for product in products:
            installed = installed_dir.findByProduct(product.getHash())

            if installed:
                installed_products.append(installed)

        return installed_products

    def _update_progress_renderer(self, column, cell_renderer, tree_model, iter):
        hide_progress = tree_model.get_value(iter, self.store['is_group_row'])
        background_color = tree_model.get_value(iter, self.store['background'])

        cell_renderer.set_property('visible', not hide_progress)

        self.empty_progress_renderer.set_property('visible', hide_progress)
        self.empty_progress_renderer.set_property('cell-background', background_color)
