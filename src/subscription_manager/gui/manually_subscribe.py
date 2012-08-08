#
# Registration dialog/wizard
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
from subscription_manager.gui.widgets import GladeWidget

# Ugly firstboot hack.
_screen = None


class ManuallySubscribeScreen(GladeWidget):
    widget_names = ['container', 'title']

    def __init__(self):
        GladeWidget.__init__(self, "manually_subscribe.glade")

    def set_title(self, title):
        self.title.set_text(title)


def get_screen():
    global _screen
    if not _screen:
        _screen = ManuallySubscribeScreen()
    return _screen
