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

import logging

from subscription_manager.gui import widgets
from subscription_manager.gui.utils import handle_gui_exception

import gettext
_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class RedeemDialog(widgets.GladeWidget):
    """GTK dialog for allowing the user to redeem any subscriptions
    associated with this machine.
    """
    widget_names = ['redeem_dialog', 'email_entry']

    def __init__(self, backend, consumer):
        super(RedeemDialog, self).__init__('redeem.glade')

        self.glade.signal_autoconnect({
            "on_redeem_dialog_delete_event": self._hide_callback,
            "on_close_button_clicked": self._hide_callback,
            "on_redeem_button_clicked": self._redeem,
        })

        self.backend = backend
        self.consumer = consumer

    def _redeem(self, button):
        email = self.email_entry.get_text()

        # TODO:  Validate email address?
        try:
            self.backend.uep.activateMachine(self.consumer.uuid, email)
            self.hide()
        except Exception, e:
            handle_gui_exception(e,
                _("Error redeeming subscription: %s"),
                self.redeem_dialog)

    # Pulled from facts dialog - TODO:  Refactor!
    def show(self):
        """Make this dialog visible."""
        self.redeem_dialog.present()

    def hide(self):
        """Make this dialog invisible."""
        self.redeem_dialog.hide()

    def set_parent_window(self, window):
        self.redeem_dialog.set_transient_for(window)

    def _hide_callback(self, button, event=None):
        """ Callback for cancel button and window closed. """
        self.hide()

        # Stop the gtk signal from propogating
        return True
