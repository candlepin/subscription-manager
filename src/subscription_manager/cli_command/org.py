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
import readline
import six.moves

from subscription_manager.cli_command.user_pass import UserPassCommand
from subscription_manager.i18n import ugettext as _


class OrgCommand(UserPassCommand):
    """
    Abstract class for commands that require an org.
    """
    def __init__(self, name, shortdesc=None, primary=False):
        super(OrgCommand, self).__init__(name, shortdesc, primary)
        self._org = None
        if not hasattr(self, "_org_help_text"):
            self._org_help_text = _("specify organization")
        self.parser.add_option(
            "--org",
            dest="org",
            metavar="ORG_KEY",
            help=self._org_help_text
        )

    @staticmethod
    def _get_org(org):
        while not org:
            org = six.moves.input(_("Organization: "))
            readline.clear_history()
        return org

    @property
    def org(self):
        if not self._org:
            owners = self.cp.getOwnerList(self.options.username)
            if len(owners) == 1:
                self._org = owners[0]['key']
            else:
                self._org = self._get_org(self.options.org)
        return self._org
