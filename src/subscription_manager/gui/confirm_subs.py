# Confirm Subs Screen: A GUI screen used to display subscriptions that
# will be applied to the system.
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
from subscription_manager.gui import widgets

class ConfirmSubscriptionsScreen(widgets.GladeWidget):

    """ Confirm Subscriptions GUI Window """
    def __init__(self):
        widget_names = [
                'confirm_subs_vbox',
                'subs_treeview',
        ]
        super(ConfirmSubscriptionsScreen,
                self).__init__('confirmsubs.glade', widget_names)

    def get_main_widget(self):
        """
        Returns the main widget to be shown in a wizard that is using
        this screen.
        """
        return self.confirm_subs_vbox

    def load_data(self, sla_data_map):
        """
        Loads the data into this screen. sla_data_map is a map
        of sla_name to DryRunResult objects.
        """
        # TODO: Implement ME.
        pass
