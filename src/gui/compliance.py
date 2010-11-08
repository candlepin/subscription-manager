# Subscription Manager Compliance Assistant
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

import os
import gtk
import logging
import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

from dateselect import DateSelector
from widgets import SubDetailsWidget

prefix = os.path.dirname(__file__)
COMPLIANCE_GLADE = os.path.join(prefix, "data/compliance.glade")

PRODUCT_NAME_INDEX = 0
CONTRACT_INDEX = 1
EXPIRATION_INDEX = 2

class ComplianceAssistant(object):
    """ Compliance Assistant GUI window. """
    def __init__(self):
        self.compliance_xml = gtk.glade.XML(COMPLIANCE_GLADE)
        self.window = self.compliance_xml.get_widget('compliance_assistant_window')
        self.uncompliant_store = gtk.ListStore(str, str, str)
        self.uncompliant_treeview = self.compliance_xml.get_widget(
                'uncompliant_products_treeview')
        self.uncompliant_treeview.set_model(self.uncompliant_store)
        self._display_uncompliant()

    def _display_uncompliant(self):
        # These display the list of products uncompliant on the selected date:
        self.uncompliant_store.clear()
        self._add_column(_('Product'), PRODUCT_NAME_INDEX)
        self._add_column(_('Contract'), CONTRACT_INDEX)
        self._add_column(_('Expiration'), EXPIRATION_INDEX)

        self.uncompliant_store.append(['Fake Product 1', 'FAKE01010010', '2010-01-01'])
        self.uncompliant_store.append(['Fake Product 2', 'N/A', 'N/A'])

        # Dummy data for now:

    def _display_providing_subs(self):
        pass

    def show(self):
        self.window.show()

    def _add_column(self, name, order):
        column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)
        self.uncompliant_treeview.append_column(column)
