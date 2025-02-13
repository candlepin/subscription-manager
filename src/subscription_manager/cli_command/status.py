#
# Subscription manager command line utility.
#
# Copyright (c) 2021 Red Hat, Inc.
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


from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)


class StatusCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Show status information for this system")
        super(StatusCommand, self).__init__("status", shortdesc, True)

    def require_connection(self):
        return False

    def _print_status_banner(self):
        print("+-------------------------------------------+")
        print("   " + _("System Status Details"))
        print("+-------------------------------------------+")

    def _do_command(self):
        """
        Print status and all reasons it is not valid
        """

        self._print_status_banner()

        # In case we are not registered, then simply print that and avoid
        # all the rest of the checks
        if not self.is_consumer_cert_present():
            print(_("Overall Status: Not registered\n"))
            return 1

        print(_("Overall Status: Registered\n"))
        return 0
