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
from subscription_manager import managerlib
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import restart_virt_who


class CleanCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Remove all local system and subscription data without affecting the server")

        super(CleanCommand, self).__init__("clean", shortdesc, False)

    def _do_command(self):
        managerlib.clean_all_data(False)
        print(_("All local data removed"))

        self._request_validity_check()

        # We have new credentials, restart virt-who
        restart_virt_who()

    def require_connection(self):
        return False
