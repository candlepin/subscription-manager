# Subscription Manager Subscription Assistant
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
import gettext
import logging
from datetime import date, datetime
from subscription_manager.managerlib import MergedPoolsStackingGroupSorter

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

import rhsm.certificate as certificate
from subscription_manager import certdirectory
from subscription_manager import managerlib
from subscription_manager import async
from subscription_manager.validity import find_first_invalid_date
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.gui import storage
from subscription_manager.gui import widgets
from subscription_manager.gui import progress
from subscription_manager.gui.utils import handle_gui_exception, make_today_now, errorWindow,\
    get_cell_background_color, set_background_model_index
from subscription_manager.quantity import QuantityDefaultValueCalculator, valid_quantity, \
                                            allows_multi_entitlement
from subscription_manager.jsonwrapper import PoolWrapper


class MappedListTreeView(gtk.TreeView):

    def add_toggle_column(self, name, column_number, callback):
        toggle_renderer = gtk.CellRendererToggle()
        toggle_renderer.set_property("activatable", True)
        toggle_renderer.set_radio(False)
        toggle_renderer.connect("toggled", callback)
        column = gtk.TreeViewColumn(name, toggle_renderer, active=column_number)
        self.append_column(column)
        return column

    def add_column(self, name, column_number, expand=False, xalign=None):
        text_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(name, text_renderer, text=column_number)
        self.store = self.get_model()
        column.set_expand(expand)
        if xalign:
            text_renderer.set_property("xalign", xalign)

        self.append_column(column)
        return column

    def add_date_column(self, name, column_number, expand=False):
        date_renderer = widgets.CellRendererDate()
        column = gtk.TreeViewColumn(name, date_renderer, text=column_number)
        self.store = self.get_model()
        if expand:
            column.set_expand(True)
        else:
            column.add_attribute(date_renderer, 'xalign', self.store['align'])

        self.append_column(column)
        return column

    def add_editable_column(self, name, column_number, renderer, edit_callback):
        renderer.set_property("editable", True)
        renderer.connect("edited", edit_callback)
        column = gtk.TreeViewColumn(name, renderer, text=column_number)
        self.store = self.get_model()
        self.append_column(column)
        return column


class SubscriptionAssistant(widgets.GladeWidget):

    """ Subscription Assistant GUI window. """
    def __init__(self, backend, consumer, facts, ent_dir=None, prod_dir=None):
        widget_names = ['subscription_label',
                        'providing_subs_label',
                        'window',
                        'invalid_window',
                        'subscriptions_window',
                        'details_window',
                        'first_invalid_radiobutton',
                        'invalid_date_radiobutton',
                        'subscribe_button',
                        'date_picker_hbox',
                        'invalid_checkbutton',
                        'edit_quantity_label']
        super(SubscriptionAssistant,
                self).__init__('subscription_assistant.glade', widget_names)

        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.pool_stash = managerlib.PoolStash(self.backend, self.consumer,
                self.facts)

        self.product_dir = prod_dir or certdirectory.ProductDirectory()
        self.entitlement_dir = ent_dir or certdirectory.EntitlementDirectory()

        # Setup initial last valid date:
        self.last_valid_date = self._load_last_valid_date()
        self.cached_date = self.last_valid_date

        invalid_type_map = {'active': bool,
                            'product_name': str,
                            'contract': str,
                            'end_date': str,
                            'entitlement_id': str,
                            'product_id': str,
                            'entitlement': gobject.TYPE_PYOBJECT,
                            'align': float}

        self.window.connect('delete_event', self.hide)
        self.invalid_store = storage.MappedListStore(invalid_type_map)
        self.invalid_treeview = MappedListTreeView(self.invalid_store)

        self.invalid_treeview.get_accessible().set_name(_("Invalid Product List"))

        self.invalid_treeview.add_toggle_column(None,
                                                self.invalid_store['active'],
                                                self._on_invalid_active_toggled)
        self.invalid_treeview.add_column(_("Product"),
                self.invalid_store['product_name'], expand=True)
        self.invalid_treeview.add_date_column(_("End Date"),
                self.invalid_store['end_date'], expand=True)
        self.invalid_treeview.set_model(self.invalid_store)
        self.invalid_window.add(self.invalid_treeview)
        self.invalid_treeview.show()

        subscriptions_type_map = {
            'product_name': str,
            'total_contracts': int,
            'total_subscriptions': int,
            'available_subscriptions': str,
            'quantity_to_consume': int,
            'pool_ids': gobject.TYPE_PYOBJECT,
            'multi-entitlement': bool,
            'virt_only': bool,
            'background': str,
            'quantity_available': int
        }

        self.subscriptions_store = storage.MappedTreeStore(subscriptions_type_map)
        self.subscriptions_treeview = MappedListTreeView(self.subscriptions_store)
        self.subscriptions_treeview.get_accessible().set_name(_("Subscription List"))
        # Disable automatic striping. This is to allow consecutive rows of the
        # same color for stacking groups.
        self.subscriptions_treeview.set_rules_hint(False)

        self.subscriptions_treeview.add_column(_('Subscription'),
                self.subscriptions_store['product_name'], expand=True)

        column = widgets.MachineTypeColumn(self.subscriptions_store['virt_only'])
        self.subscriptions_treeview.append_column(column)

        column = self.subscriptions_treeview.add_column(_("Available Subscriptions"),
                        self.subscriptions_store['available_subscriptions'], expand=False,
                        xalign=0.5)

        column = widgets.MultiEntitlementColumn(
                self.subscriptions_store['multi-entitlement'])
        self.subscriptions_treeview.append_column(column)

        # Set up editable quantity column.
        quantity_col = widgets.QuantitySelectionColumn(_("Quantity"),
                                        self.subscriptions_store['quantity_to_consume'],
                                        self.subscriptions_store['multi-entitlement'],
                                        self.subscriptions_store['quantity_available'])
        self.subscriptions_treeview.append_column(quantity_col)

        self.edit_quantity_label.set_label(quantity_col.get_column_legend_text())

        self.subscriptions_treeview.set_model(self.subscriptions_store)
        self.subscriptions_treeview.get_selection().connect('changed',
                self._on_subscription_selection)
        set_background_model_index(self.subscriptions_treeview,
                                   self.subscriptions_store['background'])

        # Connect row expansion/collapse callback
        self.subscriptions_treeview.connect("row_activated",
                                widgets.expand_collapse_on_row_activated_callback)

        self.subscriptions_window.add(self.subscriptions_treeview)
        self.subscriptions_treeview.show()

        self.sub_details = widgets.SubDetailsWidget(show_contract=False)
        self.details_window.add(self.sub_details.get_widget())

        self.first_invalid_radiobutton.set_active(True)

        self.date_picker = widgets.DatePicker(date.today())
        self.date_picker_hbox.pack_start(self.date_picker, False, False)
        self.date_picker.show_all()

        self.subscribe_button.connect('clicked', self.subscribe_button_clicked)

        self.glade.signal_autoconnect({
            "on_update_button_clicked": self._check_for_date_change,
            "on_invalid_checkbutton_toggled":
                    self._on_invalid_checkbutton_toggled,
        })

        # used for automatically setting the check all toggle
        self.programatic_invalid_toggle = False

        self.pb = None
        self.timer = None

    def show(self):
        """
        Called by the main window when this page is to be displayed.
        """
        try:
            self.window.show()
            self.subscribe_button.set_sensitive(False)
            self._reload_screen()
        except Exception, e:
            handle_gui_exception(e, _("Error displaying Subscription Assistant. Please see /var/log/rhsm/rhsm.log for more information."),
                    self.window, formatMsg=False)

    def set_parent_window(self, window):
        self.window.set_transient_for(window)

    def _reload_callback(self, product_ids, error):
        if self.pb:
            self.pb.hide()
            gobject.source_remove(self.timer)
            self.pb = None
            self.timer = None

        if error:
            handle_gui_exception(error,
                                 _("Unable to search for subscriptions"),
                                 self.window, formatMsg=False)
        else:
            # order here is important, to show subs that match the
            # reselected products.
            self._display_invalid()
            self._reselect_products(product_ids)
            self._display_subscriptions()

    def _reload_screen(self):
        """
        Draws the entire screen, called when window is shown, or something
        changes and we need to refresh.
        """
        log.debug("reloading screen")
        # end date of first subs to expire

        self.last_valid_date = self._load_last_valid_date()

        invalid_date = self._get_invalid_date()
        log.debug("using invalid date: %s" % invalid_date)
        if self.last_valid_date:
            formatted = self.format_date(self.last_valid_date)
            self.subscription_label.set_label("<big><b>%s</b></big>" % \
                    (_("Software entitlements valid until %s") % formatted))
            self.subscription_label.set_line_wrap(True)
            self.subscription_label.connect("size-allocate", self._label_allocate)
            self.first_invalid_radiobutton.set_label(
                    _("%s (first date of invalid entitlements)") % formatted)
            self.providing_subs_label.set_label(
                    _("The following subscriptions will cover the products selected on %s") % invalid_date.strftime("%x"))

        # grab a list of the highlighted products, so we can reselect them
        # after we refresh the screen (less any ones that are covered by a
        # subscription)
        product_ids = self._get_selected_product_ids()

        async_stash = async.AsyncPool(self.pool_stash)
        async_stash.refresh(invalid_date, self._reload_callback, product_ids)

        # show pulsating progress bar while we wait for results
        self.pb = progress.Progress(
                _("Searching for subscriptions. Please wait."))
        self.timer = gobject.timeout_add(100, self.pb.pulse)
        self.pb.set_parent_window(self.window)

    def _reselect_products(self, product_ids):
        """
        Reselect previously selected invalid products.
        Used after a screen reload.
        """
        for row in self.invalid_store:
            if row[self.invalid_store['product_id']] in product_ids:
                row[self.invalid_store['active']] = True

    def _label_allocate(self, label, allocation):
        label.set_size_request(allocation.width - 2, -1)

    def _check_for_date_change(self, widget):
        """
        Called when the invalid date selection *may* have changed.
        Several signals must be sent out to cover all situations and thus
        multiple may trigger at once. As such we need to store the
        invalid date last calculated, and compare it to see if
        anything has changed before we trigger an expensive refresh.
        """
        d = self._get_invalid_date()
        if self.cached_date != d:
            log.debug("New invalid date selected, reloading screen.")
            self.cached_date = d
            self._reload_screen()
        else:
            log.debug("No change in invalid date, skipping screen reload.")

    def _get_invalid_date(self):
        """
        Returns a datetime object for the invalid date to use based on current
        state of the GUI controls.
        """
        if self.first_invalid_radiobutton.get_active():
            return make_today_now(self.last_valid_date)
        else:
            return self.date_picker.date

    def _load_last_valid_date(self):
        """
        Return a datetime object representing the day, month, and year of
        last validity. Ignore the timestamp returned from certlib.
        """
        d = find_first_invalid_date(ent_dir=self.entitlement_dir,
                product_dir=self.product_dir, facts_dict=self.facts.get_facts())
        # If we can't calculate a first invalid date, just use current date.
        # The GUI shouldn't let the subscription assistant be called
        # in this case, this just lets the screen be instantiated.
        if not d:
            d = datetime.now()
        return datetime(d.year, d.month, d.day, tzinfo=certificate.GMT())

    def _display_invalid(self):
        """
        Displays the list of products or entitlements that will invalid on
        the selected date.
        """
        sorter = CertSorter(self.product_dir, self.entitlement_dir,
                self.facts.get_facts(),
                on_date=self._get_invalid_date())

        # These display the list of products invalid on the selected date:
        self.invalid_store.clear()

        # installed but not entitled products:
        na = _("N/A")
        for product_cert in sorter.unentitled_products.values():
            self.invalid_store.add_map({
                    'active': False,
                    'product_name': product_cert.getProduct().getName(),
                    'contract': na,
                    'end_date': na,
                    'entitlement_id': None,
                    'entitlement': None,
                    'product_id': product_cert.getProduct().getHash(),
                    'align': 0.0
                    })

        # installed and expired
        for product_id in sorter.expired_products.keys():
            ent_certs = sorter.expired_products[product_id]
            for ent_cert in ent_certs:
                product = sorter.installed_products[product_id].getProduct()
                self.invalid_store.add_map({
                        'active': False,
                        'product_name': product.getName(),
                        'contract': ent_cert.getOrder().getNumber(),
                        # is end_date when the cert expires or the orders end date? is it differnt?
                        'end_date': '%s' % self.format_date(ent_cert.validRange().end()),
                        'entitlement_id': ent_cert.serialNumber(),
                        'entitlement': ent_cert,
                        'product_id': product.getHash(),
                        'align': 0.0
                        })

    def _display_subscriptions(self):
        """
        Displays the list of subscriptions that will replace the selected
        products/entitlements that will be invalid.

        To do this, will will build a master list of all product IDs selected,
        both the top level marketing products and provided products. We then
        look for any subscription valid for the given date, which provides
        *any* of those product IDs. Note that there may be duplicate subscriptions
        shown. The user can select one subscription at a time to request an
        entitlement for, after which we will refresh the screen based on this new
        state.
        """
        self.subscriptions_store.clear()
        self.sub_details.clear()

        # this should be roughly correct for locally manager certs, needs
        # remote subs/pools as well

        # TODO: the above only hits entitlements, un-entitled products are not covered

        selected_products = self._get_selected_product_ids()
        pool_filter = managerlib.PoolFilter(self.product_dir, self.entitlement_dir)
        relevant_pools = pool_filter.filter_product_ids(
                self.pool_stash.compatible_pools.values(), selected_products)
        merged_pools = managerlib.merge_pools(relevant_pools).values()
        sorter = MergedPoolsStackingGroupSorter(merged_pools)
        for group_idx, group in enumerate(sorter.groups):
            bg_color = get_cell_background_color(group_idx)
            iter = None
            if group.name:
                iter = self.subscriptions_store.add_map(None,
                                                        self._get_parent_entry(group.name,
                                                                               bg_color))

            for entry in group.entitlements:
                quantity = entry.quantity
                quantity_available = 0
                if quantity < 0:
                    available = _('unlimited')
                    quantity_available = -1
                else:
                    available = _('%s of %s') % \
                        (entry.quantity - entry.consumed, quantity)
                    quantity_available = entry.quantity - entry.consumed

                pool_ids = []
                for pool in entry.pools:
                    pool_ids.append(pool['id'])
                default_quantity_calculator = \
                    QuantityDefaultValueCalculator(self.facts, self.entitlement_dir.list())

                self.subscriptions_store.add_map(iter, {
                    'product_name': entry.product_name,
                    'total_contracts': len(entry.pools),
                    'total_subscriptions': entry.quantity,
                    'available_subscriptions': available,
                    'quantity_to_consume': default_quantity_calculator.calculate(pool),
                    'pool_ids': pool_ids,
                    'multi-entitlement': allows_multi_entitlement(pool),
                    'virt_only': PoolWrapper(pool).is_virt_only(),
                    'background': bg_color,
                    'quantity_available': quantity_available,
                })
        # Ensure that the tree is fully expanded
        self.subscriptions_treeview.expand_all()

    def _get_parent_entry(self, name, bg_color):
        return {
            'product_name': name,
            'total_contracts': 0,
            'total_subscriptions': 0,
            'available_subscriptions': '',
            'quantity_to_consume': 0,
            'pool_ids': [],
            'multi-entitlement': False,
            'virt_only': False,
            'background': bg_color,
            'quantity_available': 0,
        }

    def _get_selected_product_ids(self):
        """
        Builds a master list of all product IDs for the selected invalid
        products/entitlements. In the case of entitlements which will be expired,
        we assume you want to keep all provided products you have now, so these
        provided product IDs will be included in the list.
        """
        all_product_ids = []
        for row in self.invalid_store:
            if row[self.invalid_store['active']]:
                ent_cert = row[self.invalid_store['entitlement']]
                if not ent_cert:
                    # This must be a completely unentitled product installed, just add it's
                    # top level product ID:
                    # TODO: can these product certs have provided products as well?
                    all_product_ids.append(row[self.invalid_store['product_id']])
                else:
                    for product in ent_cert.getProducts():
                        all_product_ids.append(product.getHash())
        log.debug("Calculated all selected invalid product IDs:")
        log.debug(all_product_ids)
        return all_product_ids

    def _on_invalid_active_toggled(self, cell, path):
        """
        Triggered whenever the user checks one of the products/entitlements
        in the invalid section of the UI.
        """
        treeiter = self.invalid_store.get_iter_from_string(path)
        item = self.invalid_store.get_value(treeiter, self.invalid_store['active'])
        self.invalid_store.set_value(treeiter, self.invalid_store['active'], not item)

        # refresh subscriptions
        self._display_subscriptions()

        # check the state of all rows, to see if we should turn on/off
        # the check all button
        all_active = True
        for row in self.invalid_store:
            if row[self.invalid_store['active']]:
                continue
            else:
                all_active = False
                break
        self.programatic_invalid_toggle = True
        self.invalid_checkbutton.set_property("active", all_active)
        self.programatic_invalid_toggle = False

    def _on_invalid_checkbutton_toggled(self, button):
        """
        Triggered when the user presses the check all toggle button,
        to select or unselect all invalid products
        """
        # skip execution if this is from the user selecting all rows by hand
        if self.programatic_invalid_toggle:
            return

        active = button.get_active()
        for row in self.invalid_store:
            row[self.invalid_store['active']] = active
        self._display_subscriptions()

    def format_date(self, date):
        return managerlib.formatDate(date)

    def hide(self, widget, event, data=None):
        self.window.hide()
        return True

    def _on_subscription_selection(self, widget):
        """ Handles the selection change in the subscription table. """
        model, tree_iter = widget.get_selected()

        # Handle no selection in table.
        if not tree_iter:
            # nothing selected, gray out subscribe button
            self.subscribe_button.set_sensitive(False)
            return

        self._update_sub_details(model, tree_iter)

    def _update_sub_details(self, model, selected_tree_iter):
        """ Shows details for the current selected pool. """
        has_children = model.iter_n_children(selected_tree_iter) > 0
        if not has_children and selected_tree_iter:
            product_name = model.get_value(selected_tree_iter, self.subscriptions_store['product_name'])
            pool_ids = model.get_value(selected_tree_iter, self.subscriptions_store['pool_ids'])
            provided = self.pool_stash.lookup_provided_products(pool_ids[0])
            self.sub_details.show(product_name, products=provided)
            self.subscribe_button.set_sensitive(True)
        else:
            self.sub_details.clear()
            self.subscribe_button.set_sensitive(False)

    def subscribe_button_clicked(self, button):
        model, tree_iter = self.subscriptions_treeview.get_selection().get_selected()
        pool_ids = model.get_value(tree_iter, self.subscriptions_store['pool_ids'])
        quantity_to_consume = model.get_value(tree_iter,
            self.subscriptions_store['quantity_to_consume'])
        available = model.get_value(tree_iter,
            self.subscriptions_store['quantity_available'])

        if not valid_quantity(quantity_to_consume):
            errorWindow(_("Quantity must be a positive number."),
                    parent=self.window)
            return
        if int(available) < int(quantity_to_consume):
            errorWindow(_("A quantity of %s is not available."
                          % quantity_to_consume))
            return

        for pool_id in pool_ids:
	    try:
                if(pool_id == ''):
                    break
                pool = self.pool_stash.all_pools[pool_id]
                available = pool['quantity'] - pool['consumed']
                consume = 0
                if  available >= quantity_to_consume:
                    consume = quantity_to_consume
                    quantity_to_consume = 0
                else:
                    consume = available
                    quantity_to_consume = quantity_to_consume - available

	        self.backend.uep.bindByEntitlementPool(self.consumer.uuid, pool['id'],
	                                           consume)
                if quantity_to_consume == 0:
                    break

	    except Exception, e:
	        handle_gui_exception(e, _("Error getting subscription: %s"))

        managerlib.fetch_certificates(self.backend)
        self._reload_screen()
