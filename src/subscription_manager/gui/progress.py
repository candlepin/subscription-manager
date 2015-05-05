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

from gi.repository import Gdk

from subscription_manager.gui import widgets


class Progress(widgets.SubmanBaseWidget):

    widget_names = ['progressWindow', 'progressLabel', 'progressBar', 'statusLabel']
    gui_file = "progress.glade"

    def __init__(self, title, label):
        super(Progress, self).__init__()

        self.progressWindow.connect("delete-event", self._on_delete_event)
        cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)
        self.progressWindow.window.set_cursor(cursor)

        self.lastProgress = 0.0

        self.set_title(title)
        self.set_label(label)

    def hide(self):
        self.progressWindow.hide()
        del self

    def set_title(self, text):
        self.progressWindow.set_title(text)

    def set_label(self, text):
        self.progressLabel.set_text(text)

    def pulse(self):
        """
        pulse for a glib mainloop timeout callback
        """
        # If it's been closed, don't attempt to pulse
        if self.progressBar:
            self.progressBar.pulse()
            return True
        return False

    def set_progress(self, amount, total):
        if total:
            i = min(1, float(amount) / total)
        else:
            i = 1

        if i > self.lastProgress + .01 or i == 1:
            self.progressBar.set_fraction(i)
            if i == 1:
                # reset
                i = 0
            self.lastProgress = i

    def set_status_label(self, text):
        self.statusLabel.set_text(text)

    def set_parent_window(self, window):
        self.progressWindow.set_transient_for(window)

    def _on_delete_event(self, widget, event):
        # Block the progress bar from closing until we hide it
        return True
