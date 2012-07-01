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

import logging
import gettext
import os
from subscription_manager.gui import widgets

_ = gettext.gettext
log = logging.getLogger('rhsm-app.' + __name__)

prefix = os.path.dirname(__file__)
GLADE_XML = os.path.join(prefix, "data/filters.glade")


class Filters(object):
    def __init__(self, show_compatible=False, show_no_overlapping=False,
            show_installed=False, contains_text=""):
        self.show_compatible = show_compatible
        self.show_no_overlapping = show_no_overlapping
        self.show_installed = show_installed
        self.contains_text = contains_text


class FilterOptionsWindow(widgets.GladeWidget):
    def __init__(self, filters, parent):
        widgets = ['filter_product_window', 'compatible_checkbutton',
                'installed_checkbutton', 'no_overlapping_checkbutton',
                'contains_text_entry']
        super(FilterOptionsWindow, self).__init__(GLADE_XML, widgets)
        self.filters = filters
        self.parent = parent
        self.filter_product_window.connect("delete-event", self.deleted)
        self.glade.signal_autoconnect({
            "on_clear_button_clicked": self.clear_button_clicked,
            "on_close_button_clicked": self.close_button_clicked,
            "on_apply_button_clicked": self.apply_button_clicked,
            })

    def clear_button_clicked(self, button):
        self.compatible_checkbutton.set_active(False)
        self.installed_checkbutton.set_active(False)
        self.no_overlapping_checkbutton.set_active(False)
        self.contains_text_entry.set_text("")

    def show(self):
        self.compatible_checkbutton.set_active(self.filters.show_compatible)
        self.installed_checkbutton.set_active(self.filters.show_installed)
        self.no_overlapping_checkbutton.set_active(self.filters.show_no_overlapping)
        self.contains_text_entry.set_text(self.filters.contains_text)
        self.filter_product_window.present()

    def apply_button_clicked(self, button):
        new_filter = Filters()
        new_filter.show_compatible = self.compatible_checkbutton.get_active()
        new_filter.show_installed = self.installed_checkbutton.get_active()
        new_filter.show_no_overlapping = self.no_overlapping_checkbutton.get_active()
        new_filter.contains_text = self.contains_text_entry.get_text()

        self.parent.filters = new_filter
        log.debug("filters changed: %s" % new_filter.__dict__)
        self.parent.display_pools()
        self.parent.update_applied_filters_label()
        self.filter_product_window.destroy()

    def deleted(self, event, data):
        self.filter_product_window.destroy()

    def close_button_clicked(self, button):
        self.filter_product_window.destroy()
