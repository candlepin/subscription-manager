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

import gettext
import logging

from subscription_manager import ga
from subscription_manager.gui import widgets

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class Filters(object):
    def __init__(self, show_compatible=False, show_no_overlapping=False,
            show_installed=False, contains_text=""):
        self.show_compatible = show_compatible
        self.show_no_overlapping = show_no_overlapping
        self.show_installed = show_installed
        self.contains_text = contains_text

    def get_applied_count(self):
        return len(filter(None, self.__dict__.values()))


class FilterOptionsWindow(widgets.SubmanBaseWidget):
    widget_names = ['filter_product_window', 'compatible_checkbutton',
                    'installed_checkbutton', 'no_overlapping_checkbutton',
                    'contains_text_entry']
    gui_file = "filters.glade"

    def __init__(self, filters, parent):

        super(FilterOptionsWindow, self).__init__()
        self.filters = filters
        self.parent = parent

        # Center on parent when opened.
        self.filter_product_window.set_position(ga.Gtk.WindowPosition.CENTER_ON_PARENT)
        self.filter_product_window.set_transient_for(self.parent.parent_win)

        # Set all the filters to their default values before the signals are
        # connected.  Otherwise, their callbacks will be triggered when we
        # call set_active().
        self.set_initial_widget_state()
        self.connect_signals({
            "on_filter_product_window_delete_event": self.deleted,
            "on_clear_button_clicked": self.clear_button_clicked,
            "on_close_button_clicked": self.close_button_clicked,
            "on_contains_text_entry_changed": self.update_filters,
            "on_compatible_checkbutton_toggled": self.update_filters,
            "on_installed_checkbutton_toggled": self.update_filters,
            "on_no_overlapping_checkbutton_toggled": self.update_filters,
            })

    def clear_button_clicked(self, widget):
        self.compatible_checkbutton.set_active(False)
        self.installed_checkbutton.set_active(False)
        self.no_overlapping_checkbutton.set_active(False)
        self.contains_text_entry.set_text("")

    def set_initial_widget_state(self):
        self.compatible_checkbutton.set_active(self.filters.show_compatible)
        self.installed_checkbutton.set_active(self.filters.show_installed)
        self.no_overlapping_checkbutton.set_active(self.filters.show_no_overlapping)
        self.contains_text_entry.set_text(self.filters.contains_text)

    def show(self):
        self.filter_product_window.present()

    def update_filters(self, widget):
        new_filter = Filters()
        new_filter.show_compatible = self.compatible_checkbutton.get_active()
        new_filter.show_installed = self.installed_checkbutton.get_active()
        new_filter.show_no_overlapping = self.no_overlapping_checkbutton.get_active()
        new_filter.contains_text = self.contains_text_entry.get_text()

        self.parent.filters = new_filter
        self.filters = new_filter
        log.debug("filters changed: %s" % new_filter.__dict__)
        self.parent.display_pools()
        self.parent.update_applied_filters_label()

    def deleted(self, event, data):
        self.filter_product_window.hide()
        # See http://faq.pyGtk.org/index.py?req=show&file=faq10.006.htp
        return True

    def close_button_clicked(self, widget):
        self.filter_product_window.hide()
