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

prefix = os.path.dirname(__file__)
DATE_SELECT_GLADE = os.path.join(prefix, "data/dateselect.glade")


class DateSelector(object):

    def __init__(self, callback):
        """
        Pass callback to be run when a date is selected by the user.
        """
        self.date_select_xml = gtk.glade.XML(DATE_SELECT_GLADE)
        self.window = self.date_select_xml.get_widget(
                'date_select_window')
        self.calendar = self.date_select_xml.get_widget(
                'calendar')
        self.callback = callback
        self.date_select_xml.signal_autoconnect({
            "on_calendar_day_selected_double_click": self.date_selected,
        })

    def date_selected(self, widget):
        self.hide()
        # Execute the callback we were provided:
        self.callback(widget)

    def show(self):
        self.window.show()

    def hide(self):
        self.window.hide()
