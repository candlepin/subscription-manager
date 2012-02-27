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

import os
import gtk
import logging

import gettext
_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

from subscription_manager.gui.utils import GladeWrapper
from subscription_manager.gui.confirm_subs import ConfirmSubscriptionsScreen

DATA_PREFIX = os.path.dirname(__file__)
AUTOBIND_XML = GladeWrapper(os.path.join(DATA_PREFIX, "data/autobind.glade"))

class AutobindWizard:
    """
    Autobind Wizard: Manages screenflow used in several places in the UI.
    """

    def __init__(self, backend, consumer):
        """
        Create the Autobind wizard.

        backend - A managergui.Backend object.
        consumer - A managergui.Consumer object.
        """
        log.debug("Launching autobind wizard.")
        self.backend = backend
        self.consumer = consumer
        self.owner_key = self.backend.uep.getOwner(
                self.consumer.getConsumerId())['key']

        signals = {
        }

        AUTOBIND_XML.signal_autoconnect(signals)
        self.main_window = AUTOBIND_XML.get_widget("autobind_dialog")
        self.main_window.set_title(_("Subscribe System"))
        self.notebook = AUTOBIND_XML.get_widget("autobind_notebook")

        self._setup_screens()

        self._find_suitable_service_levels()

    def _find_suitable_service_levels(self):
        # Figure out what screen to display initially:
        # TODO: what if we already have an SLA selected?
        # TODO: what if we have no installed products?
        self.available_slas = self.backend.uep.getServiceLevelList(
                self.owner_key)
        log.debug("Available service levels: %s" % self.available_slas)
        # Will map service level (string) to the results of the dry-run
        # autobind results for each SLA that covers all installed products:
        self.suitable_slas = {}
        for sla in self.available_slas:
            dry_run = self.backend.uep.dryRunBind(self.consumer.uuid,
                    sla)
            log.debug("Dry run results: %s" % dry_run)

    def _setup_screens(self):
        self.screens = [
                ConfirmSubscriptionsScreen(),
        ]
        # TODO: this probably won't work, the screen flow is too conditional,
        # so we'll likely need to hard code the screens, and hook up logic
        # to the back button somehow

        # For each screen configured in this wizard, create a tab:
        for screen in self.screens:
            widget = screen.get_main_widget()
            widget.unparent()
            widget.reparent(self.notebook)
            self.notebook.append_page(widget)

    def show(self):
        self.main_window.show()

