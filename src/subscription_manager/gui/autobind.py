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

    def get_title(self):
        """
        Gets the title for this screen.
        """
        raise NotImplementedError("Screen object must implement: get_title()")

    def get_main_widget(self):
        """
        Returns the widget that contains the main content of the screen.
        Since we use glade to design our screens, we create our screen
        content inside a parent window object, and return the first child.
        """
        raise NotImplementedError("Screen object must implement: get_main_widget()")


class AutobindWizard(widgets.GladeWidget):
    """
    Autobind Wizard: Manages screenflow used in several places in the UI.
    """

    def __init__(self, backend, consumer, facts):
        """
        Create the Autobind wizard.

        backend - A managergui.Backend object.
        consumer - A managergui.Consumer object.
        """
        log.debug("Launching autobind wizard.")

        widget_names = [
                'autobind_dialog',
                'autobind_notebook',
        ]
        widgets.GladeWidget.__init__(self, "autobind.glade", widget_names)

        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.prod_dir = self.backend.product_dir
        self.ent_dir = self.backend.entitlement_dir

        self.owner_key = self.backend.uep.getOwner(
                self.consumer.getConsumerId())['key']

        # Using the current date time, we may need to expand this to work
        # with arbitrary dates for future entitling someday:
        # TODO: what if no products need entitlements?
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                self.facts.get_facts())

        signals = {
        }
        self.glade.signal_autoconnect(signals)

        self._setup_screens()
        self._find_suitable_service_levels()

    def _find_suitable_service_levels(self):
        # Figure out what screen to display initially:
        # TODO: what if we already have an SLA selected?
        # TODO: test no SLA's available
        # TODO: test no results are returned for any SLA
        self.available_slas = self.backend.uep.getServiceLevelList(
                self.owner_key)
        log.debug("Available service levels: %s" % self.available_slas)
        # Will map service level (string) to the results of the dry-run
        # autobind results for each SLA that covers all installed products:
        self.suitable_slas = {}
        for sla in self.available_slas:
            dry_run_json = self.backend.uep.dryRunBind(self.consumer.uuid,
                    sla)
            log.debug("Dry run results: %s" % dry_run_json)
            dry_run = DryRunResult(sla, dry_run_json, self.sorter)
            log.debug(dry_run.covers_required_products())

            if dry_run.covers_required_products():
                self.suitable_slas[sla] = dry_run

    def _setup_screens(self):
        self.screens = {
                CONFIRM_SUBS: ConfirmSubscriptionsScreen(self),
                SELECT_SLA: SelectSLAScreen(self),
        }
        # TODO: this probably won't work, the screen flow is too conditional,
        # so we'll likely need to hard code the screens, and hook up logic
        # to the back button somehow

        # For each screen configured in this wizard, create a tab:
        for screen in self.screens.values():
            if not isinstance(screen, AutobindWizardScreen):
                raise RuntimeError("AutobindWizard screens must implement type" + \
                                   "AutobindWizardScreen")
            widget = screen.get_main_widget()
            widget.unparent()
            widget.show()
            self.autobind_notebook.append_page(widget)

    def show(self):
        self._load_initial_screen()
        self.autobind_dialog.show()

    def _load_initial_screen(self):
        if len(self.suitable_slas) == 1:
            self.show_confirm_subs(self.suitable_slas.keys()[0])
        elif len(self.suitable_slas) > 1:
            self.show_select_sla()
        else:
            # TODO: Show advanced or error message
            pass

    def show_confirm_subs(self, service_level):
        confirm_subs_screen = self.screens[CONFIRM_SUBS]
        self.autobind_notebook.set_current_page(CONFIRM_SUBS)
        self.autobind_dialog.set_title(confirm_subs_screen.get_title())
        confirm_subs_screen.load_data(self.suitable_slas[service_level])

    def show_select_sla(self):
        select_sla_screen = self.screens[SELECT_SLA]
        self.autobind_notebook.set_current_page(SELECT_SLA)
        self.autobind_dialog.set_title(select_sla_screen.get_title())
        select_sla_screen.load_data(self.suitable_slas)


class ConfirmSubscriptionsScreen(AutobindWizardScreen, widgets.GladeWidget):

    """ Confirm Subscriptions GUI Window """
    def __init__(self, wizard):
        widget_names = [
                'confirm_subs_vbox',
                'subs_treeview',
        ]
        AutobindWizardScreen.__init__(self, wizard)
        widgets.GladeWidget.__init__(self, 'confirmsubs.glade', widget_names)

        self.store = gtk.ListStore(str)
        self.store.append(["Pool 1"])
        self.store.append(["Pool 2"])

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

    def get_title(self):

        return _("Confirm Subscription(s)")
    def get_main_widget(self):
        """
        Returns the main widget to be shown in a wizard that is using
        this screen.
        """
        return self.confirm_subs_vbox

    def load_data(self, dry_run_result):
        # TODO: Implement ME.
        print("Selected SLA is %s" % dry_run_result.service_level)


class SelectSLAScreen(AutobindWizardScreen, widgets.GladeWidget):
    """
    An autobind wizard screen that displays the  available
    SLAs that are provided by the installed products.
    """

    def __init__(self, wizard):
        widget_names = [
            'main_content',
            'detection_label',
            'detected_products_label',
            'product_list_label',
            'subscribe_all_as_label',
            'sla_radio_container'
        ]

        AutobindWizardScreen.__init__(self, wizard)
        widgets.GladeWidget.__init__(self, 'selectsla.glade', widget_names)

        signals = {
            'on_back_button_clicked': self._back,
            'on_forward_button_clicked': self._forward,
        }
        self.glade.signal_autoconnect(signals)

    def get_title(self):
        return _("Select Service Level Agreement")

    def get_main_widget(self):
        """
        Returns the content widget for this screen.
        """
        return self.main_content

    def load_data(self, sla_data_map):
        self._clear_buttons()
        group = None
        for sla in sla_data_map:
            radio = gtk.RadioButton(group = group, label = sla)
            self.sla_radio_container.pack_start(radio)
            radio.show()
            group = radio

    def _back(self, button):
        pass

    def _forward(self, button):
        self.wizard.show_confirm_subs("Standard")

    def _clear_buttons(self):
        child_widgets = self.sla_radio_container.get_children()
        for child in child_widgets:
            self.sla_radio_container.remove(child)

