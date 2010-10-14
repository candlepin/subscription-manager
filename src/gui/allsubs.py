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

import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

prefix = os.path.dirname(__file__)
ALL_SUBS_GLADE = os.path.join(prefix, "data/allsubs.glade")

class AllSubscriptionsTab(object):

    def __init__(self, main_window):
        self.main_win = main_window

        self.all_subs_xml = gtk.glade.XML(ALL_SUBS_GLADE)
        self.all_subs_vbox = self.all_subs_xml.get_widget('all_subs_vbox')

        self.all_subs_store = gtk.ListStore(str, str, str, str, str)
        self.all_subs_view = self.all_subs_xml.get_widget('all_subs_treeview')
        self.all_subs_view.set_model(self.all_subs_store)
        self._add_column(_("Subscription"), 0)
        self._add_column(_("# Bundled Products"), 0)
        self._add_column(_("Total Contracts"), 0)
        self._add_column(_("Total Subscriptions"), 0)
        self._add_column(_("Available Subscriptions"), 0)
        self.load_all_subs()
        
    def load_all_subs(self):
        self.all_subs_store.clear()
        self.all_subs_store.append(['RHEL 5', '10', '10,000', '25,000', '1,000'])
        self.all_subs_store.append(['RHEL 6', '10', '10,000', '25,000', '1,000'])

    def _add_column(self, name, order):
        column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=order)
        self.all_subs_view.append_column(column)

    def get_content(self):
        return self.all_subs_vbox


