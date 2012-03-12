#
# GUI Module for the Autobind Wizard
#
# Copyright (c) 2012 Red Hat, Inc.
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
import logging

import gettext
_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

from subscription_manager.cert_sorter import CertSorter
from subscription_manager.gui import widgets
from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.managerlib import fetch_certificates
from subscription_manager.gui.messageWindow import InfoDialog, ErrorDialog, \
        OkDialog

# Define indexes for screens.
CONFIRM_SUBS = 0
SELECT_SLA = 1


class DryRunResult(object):
    """ Encapsulates a dry-run autobind result from the server. """

    def __init__(self, service_level, server_json, cert_sorter):
        self.json = server_json
        self.sorter = cert_sorter
        self.service_level = service_level

    def covers_required_products(self):
        """
        Return True if this dry-run result would cover all installed
        products which are not covered by a valid entitlement.

        NOTE: we do not require full stacking compliance here. The server
        will return the best match it can find, but that may still leave you
        only partially entitled. We will still consider this situation a valid
        SLA to use, the key point being you have access to the content you
        need.
        """
        required_products = set(self.sorter.unentitled_products.keys())

        # The products that would be covered if we did this autobind:
        autobind_products = set()

        log.debug("Unentitled products: %s" % required_products)
        for pool_quantity in self.json:
            pool = pool_quantity['pool']
            # This is usually the MKT product and has no content, but it
            # doesn't hurt to include it:
            autobind_products.add(pool['productId'])
            for provided_prod in pool['providedProducts']:
                autobind_products.add(provided_prod['productId'])
        log.debug("Autobind would give access to: %s" % autobind_products)
        if required_products.issubset(autobind_products):
            log.debug("Found valid service level: %s" % self.service_level)
            return True
        else:
            log.debug("Service level does not cover required products: %s" % \
                    self.service_level)
            return False

    def get_pool_quantities(self):
        """
        Returns a list of tuples, each of which is a pool ID and a quantity
        to consume. Used when we actually decide to bind to this pool.
        """
        tuples = []
        for pool_quantity in self.json:
            tuples.append((pool_quantity['pool']['id'],
                pool_quantity['quantity']))
        return tuples


class AutobindWizardScreen(object):
    """
    An object representing a screen that can be displayed by the
    AutobindWizard. Its primary purpose is to define an interface
    to the wizard object itself.
    """

    def __init__(self, wizard):
        # Maintain a reference to the parent wizard so we can reliably switch
        # to other screens and pass data along:
        self.wizard = wizard
        self.widgets = []
        self.signals = {}

    def get_title(self):
        """
        Gets the title for this screen.
        """
        raise NotImplementedError("Screen object must implement: get_title()")

    def get_forward_button_label(self):
        """
        Gets the forward button label for this screen (so you can set Subscribe
        instead of Forward)

        Return None if you want to use Forward
        """
        raise NotImplementedError(
                "Screen object must implement: get_forward_button_label()")


    def get_main_widget(self):
        """
        Returns the widget that contains the main content of the screen.
        Since we use glade to design our screens, we create our screen
        content inside a parent window object, and return the first child.
        """
        raise NotImplementedError(
                "Screen object must implement: get_main_widget()")


class AutobindWizard(widgets.GladeWidget):
    """
    Autobind Wizard: Manages screenflow used in several places in the UI.
    """

    def __init__(self, backend, consumer, facts, parent_window,
            initial_screen_back_callback=None, cancel_callback=None):
        """
        Create the Autobind wizard.

        backend - A managergui.Backend object.
        consumer - A managergui.Consumer object.
        """
        log.debug("Launching autobind wizard.")

        widget_names = [
                'autobind_dialog',
                'autobind_notebook',
                'screen_label',
                'back_button',
                'forward_button',
        ]
        widgets.GladeWidget.__init__(self, "autobind.glade", widget_names)

        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.prod_dir = self.backend.product_dir
        self.ent_dir = self.backend.entitlement_dir
        self.parent_window = parent_window

        # This signifies that the wizard is embedded by another. The
        # callback will be executed when the back button is clicked
        # on the initial screen.
        self.initial_screen_back_callback = initial_screen_back_callback

        # Optional callback to be called when the cancel button is pressed:
        self.cancel_callback = cancel_callback

        self.embedded = self.initial_screen_back_callback != None

        signals = {
                "on_cancel_button_clicked": self._cancel,
                "on_back_button_clicked": self._back,
                "on_forward_button_clicked": self._forward,
        }
        self.glade.signal_autoconnect(signals)

        # The screen display stack keeps track of screen indexes as we progress
        # through the wizard. A screen's index will be placed on the stack once
        # it has been displayed. NOTE: Showing the initial screen of the wizard
        # does not put anything on the stack.
        self.screen_display_stack = []
        self._setup_screens()
        self.autobind_dialog.set_transient_for(parent_window)

    def _cancel(self, button):
        self.destroy()
        if self.cancel_callback:
            self.cancel_callback()

    def _back(self, button):
        self.previous_screen()

    def _forward(self, button):
        self._current_screen.forward()

    def _load_data(self):
        consumer_json = self.backend.uep.getConsumer(
                self.consumer.getConsumerId())

        if 'serviceLevel' not in consumer_json:
            OkDialog(_("Unable to auto-subscribe, server does not support service levels."),
                    parent = self.parent_window)
            self.destroy()
            return

        self.owner_key = consumer_json['owner']['key']

        # This is often "", set to None in that case:
        self.current_sla = consumer_json['serviceLevel'] or None

        # Using the current date time, we may need to expand this to work
        # with arbitrary dates for future entitling someday:
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                self.facts.get_facts())

        if len(self.sorter.unentitled_products) == 0:
            InfoDialog(_("All installed products are covered by valid entitlements. No need to update certificates at this time."),
                parent = self.parent_window)
            self.destroy()
            return

        self._find_suitable_service_levels()

    def show(self):
        self._load_data()
        self._load_initial_screen()

    def _find_suitable_service_levels(self):
        if self.current_sla:
            available_slas = [self.current_sla]
            log.debug("Using system's current service level: %s" %
                    self.current_sla)
        else:
            available_slas = self.backend.uep.getServiceLevelList(
                    self.owner_key)
            log.debug("Available service levels: %s" % available_slas)

        # Will map service level (string) to the results of the dry-run
        # autobind results for each SLA that covers all installed products:
        self.suitable_slas = {}
        for sla in available_slas:
            dry_run_json = self.backend.uep.dryRunBind(self.consumer.uuid,
                    sla)
            dry_run = DryRunResult(sla, dry_run_json, self.sorter)

            # If we have a current SLA for this system, we do not need
            # all products to be covered by the SLA to proceed through
            # this wizard:
            if self.current_sla or dry_run.covers_required_products():
                self.suitable_slas[sla] = dry_run

    def _setup_screens(self):
        self._current_screen = None
        self.screens = {
                CONFIRM_SUBS: ConfirmSubscriptionsScreen(self),
                SELECT_SLA: SelectSLAScreen(self),
        }
        # For each screen configured in this wizard, create a tab:
        for screen in self.screens.values():
            if not isinstance(screen, AutobindWizardScreen):
                raise RuntimeError(
                        "AutobindWizard screens must implement type AutobindWizardScreen")
            widget = screen.get_main_widget()
            widget.unparent()
            widget.show()
            self.autobind_notebook.append_page(widget)

    def destroy(self):
        self.autobind_dialog.destroy()

    def _load_initial_screen(self):
        if len(self.suitable_slas) == 1:
            # If system already had a service level, we can hit this point
            # when we cannot fix any unentitled products:
            result = self.suitable_slas[self.suitable_slas.keys()[0]]
            if len(result.json) == 0 and self.current_sla:
                ErrorDialog(_("Unable to subscribe to any additional products at current service level: %s") %
                        self.current_sla, parent = self.parent_window)
                self.destroy()
                return
            self.show_confirm_subs(self.suitable_slas.keys()[0], initial=True)
        elif len(self.suitable_slas) > 1:
            self.show_select_sla(initial=True)
        else:
            log.info("No suitable service levels found.")
            ErrorDialog(_("No service levels will cover all installed products. "
                "Please use the \"All Available Subscriptions\" tab to manually "
                "entitle this system."), parent = self.parent_window)
            self.destroy()
            return
        self.autobind_dialog.show()

    def show_confirm_subs(self, service_level, initial=False):
        confirm_subs_screen = self._show_screen(CONFIRM_SUBS, initial)
        confirm_subs_screen.load_data(self.suitable_slas[service_level])

    def show_select_sla(self, initial=False):
        select_sla_screen = self._show_screen(SELECT_SLA, initial)
        select_sla_screen.load_data(
                set(self.sorter.unentitled_products.values()),
                self.suitable_slas)

    def _show_screen(self, screen_idx, initial):
        # Do not put the initial page on the stack as the stack should be empty
        # for the first page shown.
        if not initial:
            self.screen_display_stack.append(
                    self.autobind_notebook.get_current_page())
        screen = self.screens[screen_idx]
        self._toggle_back_button(initial)
        self.autobind_notebook.set_current_page(screen_idx)
        self.screen_label.set_label("<b>%s</b>" % screen.get_title())
        self.forward_button.set_label(screen.get_forward_button_label())
        self._current_screen = screen
        return screen

    def _toggle_back_button(self, is_initial):
        if is_initial and not self.embedded:
            self.back_button.hide()
        else:
            self.back_button.show()

    def previous_screen(self):
        if len(self.screen_display_stack) == 0:
            if self.embedded:
                self.destroy()
                self.initial_screen_back_callback()
                return
            # If not embedded, we should have not be able to click back.
            raise RuntimeError("No screens available on wizard screen stack.")

        previous_screen_idx = self.screen_display_stack.pop()
        initial = len(self.screen_display_stack) == 0
        self._show_screen(previous_screen_idx, initial)


class ConfirmSubscriptionsScreen(AutobindWizardScreen, widgets.GladeWidget):

    """ Confirm Subscriptions GUI Window """
    def __init__(self, wizard):
        AutobindWizardScreen.__init__(self, wizard)

        self.widgets.extend([
                'confirm_subs_vbox',
                'subs_treeview',
                'back_button',
                'sla_label',
        ])
        widgets.GladeWidget.__init__(self, 'confirmsubs.glade', self.widgets)

        self.glade.signal_autoconnect(self.signals)
        self.store = gtk.ListStore(str)

        # For now just going to set up one product name column, we will need
        # to display more information though.
        self.subs_treeview.set_model(self.store)
        column = gtk.TreeViewColumn(_("Subscription"))
        self.subs_treeview.append_column(column)
        # create a CellRendererText to render the data
        self.cell = gtk.CellRendererText()
        column.pack_start(self.cell, True)
        column.add_attribute(self.cell, 'text', 0)
        column.set_sort_column_id(0)
        self.subs_treeview.set_search_column(0)

    def forward(self):
        try:
            if not self.wizard.current_sla:
                log.info("Saving selected service level for this system.")
                self.wizard.backend.uep.updateConsumer(
                        self.wizard.consumer.getConsumerId(),
                        service_level=self.dry_run_result.service_level)

            log.info("Binding to subscriptions at service level: %s" %
                    self.dry_run_result.service_level)
            for pool_quantity in self.dry_run_result.json:
                pool_id = pool_quantity['pool']['id']
                quantity = pool_quantity['quantity']
                log.info("  pool %s quantity %s" % (pool_id, quantity))
                self.wizard.backend.uep.bindByEntitlementPool(
                        self.wizard.consumer.getConsumerId(), pool_id, quantity)
                fetch_certificates(self.wizard.backend)
        except Exception, e:
            # Going to try to update certificates just in case we errored out
            # mid-way through a bunch of binds:
            try:
                fetch_certificates(self.wizard.backend)
            except Exception, cert_update_ex:
                log.info("Error updating certificates after error:")
                log.exception(cert_update_ex)
            handle_gui_exception(e, _("Error subscribing:"),
                    self.wizard.autobind_dialog)

        self.wizard.destroy()

    def get_title(self):
        return _("Confirm Subscription(s)")

    def get_forward_button_label(self):
        return _("Subscribe")

    def get_main_widget(self):
        """
        Returns the main widget to be shown in a wizard that is using
        this screen.
        """
        return self.confirm_subs_vbox

    def load_data(self, dry_run_result):
        self.dry_run_result = dry_run_result

        # Make sure that the store is cleared each time
        # the data is loaded into the screen.
        self.store.clear()
        log.info("Using service level: %s" % dry_run_result.service_level)
        self.sla_label.set_markup("<b>" + dry_run_result.service_level + "</b>")

        for pool_quantity in dry_run_result.json:
            self.store.append([pool_quantity['pool']['productName']])


class SelectSLAScreen(AutobindWizardScreen, widgets.GladeWidget):
    """
    An autobind wizard screen that displays the  available
    SLAs that are provided by the installed products.
    """

    def __init__(self, wizard):
        AutobindWizardScreen.__init__(self, wizard)

        self.widgets.extend([
            'main_content',
            'product_list_label',
            'sla_radio_container',
        ])

        widgets.GladeWidget.__init__(self, 'selectsla.glade', self.widgets)

        self.glade.signal_autoconnect(self.signals)

    def get_title(self):
        return _("Select Service Level Agreement")

    def get_forward_button_label(self):
        return _("Forward")

    def get_main_widget(self):
        """
        Returns the content widget for this screen.
        """
        return self.main_content

    def load_data(self, unentitled_prod_certs, sla_data_map):
        self.product_list_label.set_text(
                self._format_prods(unentitled_prod_certs))
        self._clear_buttons()
        group = None
        for sla in sla_data_map:
            radio = gtk.RadioButton(group = group, label = sla)
            radio.connect("toggled", self._radio_clicked, sla)
            self.sla_radio_container.pack_end(radio, expand=False, fill=False)
            radio.show()
            group = radio

        # set the initial radio button as default selection.
        group.set_active(True)

    def forward(self):
        self.wizard.show_confirm_subs(self.selected_sla)

    def _clear_buttons(self):
        child_widgets = self.sla_radio_container.get_children()
        for child in child_widgets:
            self.sla_radio_container.remove(child)

    def _radio_clicked(self, button, sla):
        if button.get_active():
            self.selected_sla = sla

    def _format_prods(self, prod_certs):
        prod_str = ""
        for i, cert in enumerate(prod_certs):
            log.debug(cert)
            prod_str = "%s%s" % (prod_str, cert.getProduct().getName())
            if i + 1 < len(prod_certs):
                prod_str += ", "
        return prod_str
