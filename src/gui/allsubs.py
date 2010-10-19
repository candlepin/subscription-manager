#
# GUI Module for standalone subscription-manager cli
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
import managerlib

from facts import Facts

prefix = os.path.dirname(__file__)
ALL_SUBS_GLADE = os.path.join(prefix, "data/allsubs.glade")

class AllSubscriptionsTab(object):

    def __init__(self, backend, consumer):
        self.backend = backend
        self.consumer = consumer
        self.facts = Facts()

        self.all_subs_xml = gtk.glade.XML(ALL_SUBS_GLADE)
        self.all_subs_vbox = self.all_subs_xml.get_widget('all_subs_vbox')

        self.all_subs_xml.signal_autoconnect({
            "on_search_button_clicked": self.search_button_clicked,
        })

        self.subs_store = gtk.ListStore(str, str, str, str, str)
        self.subs_treeview = self.all_subs_xml.get_widget('all_subs_treeview')
        self.subs_treeview.set_model(self.subs_store)
        self._add_column(_("Subscription"), 0)
        self._add_column(_("# Bundled Products"), 1)
        self._add_column(_("Total Contracts"), 2)
        self._add_column(_("Total Subscriptions"), 3)
        self._add_column(_("Available Subscriptions"), 4)

        self.no_hw_match_checkbutton = self.all_subs_xml.get_widget(
                'match_hw_checkbutton')
        self.not_installed_checkbutton = self.all_subs_xml.get_widget(
                'not_installed_checkbutton')
        self.contains_text_checkbutton = self.all_subs_xml.get_widget(
                'contains_text_checkbutton')
        self.contains_text_entry = self.all_subs_xml.get_widget(
                'contain_text_entry')

    def include_incompatible(self):
        """ Return True if we're to include pools which failed a rule check. """
        return self.no_hw_match_checkbutton.get_active()

    def include_uninstalled(self):
        """ 
        Return True if we're to include pools for products that are 
        not installed.
        """
        return self.not_installed_checkbutton.get_active()

    def get_filter_text(self):
        """
        Returns the text to filter subscriptions based on. Will return None
        if the text box is empty, or the filter checkbox is not enabled.
        """
        if self.contains_text_checkbutton.get_active():
            contains_text = self.contains_text_entry.get_text()
            if contains_text != "":
                return contains_text
        return None
        
    def load_all_subs(self):
        log.debug("Loading subscriptions.")
        self.subs_store.clear()
        self.subs_store.append(['RHEL 5', '10', '10,000', '25,000', '1,000'])
        self.subs_store.append(['RHEL 6', '10', '10,000', '25,000', '1,000'])

        pools = managerlib.getAvailableEntitlements(self.backend.uep,
                self.consumer.uuid, self.facts, all=self.include_incompatible())

        # Filter out products that are not installed if necessary:
        if log.isEnabledFor(logging.debug):
            log.debug("pools:")
            for pool in pools:
                log.debug("   %s" % pool)

    def _add_column(self, name, order):
        column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)
        self.subs_treeview.append_column(column)

    def get_content(self):
        return self.all_subs_vbox

    def get_label(self):
        return _("All Available Subscriptions")

    def search_button_clicked(self, widget):
        """ Reload the subscriptions when the Search button is clicked. """
        log.debug("Search button clicked.")
        log.debug("   include hw mismatch = %s" % self.include_incompatible())
        log.debug("   include uninstalled = %s" % self.include_uninstalled())
        log.debug("   contains text = %s" % self.get_filter_text())
        self.load_all_subs()
