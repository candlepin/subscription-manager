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
import os

import rhsm.connection as connection

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import handle_exception
from subscription_manager.cli_command.list import ORG_LIST
from subscription_manager.cli_command.user_pass import UserPassCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.printing_utils import columnize, echo_columnize_callback

log = logging.getLogger(__name__)


class OwnersCommand(UserPassCommand):
    def __init__(self):
        shortdesc = _("Display the organizations against which a user can register a system")

        super(OwnersCommand, self).__init__("orgs", shortdesc, False)

        self._add_url_options()

    def _do_command(self):
        try:
            # get a UEP
            if self.options.token:
                self.cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
            else:
                self.cp_provider.set_user_pass(self.username, self.password)
                self.cp = self.cp_provider.get_basic_auth_cp()
            owners = self.cp.getOwnerList(self.username)
            log.debug("Successfully retrieved org list from server.")
            if len(owners):
                print("+-------------------------------------------+")
                print("          {name} {label}".format(name=self.username, label=_("Organizations")))
                print("+-------------------------------------------+")
                print("")
                for owner in owners:
                    print(
                        columnize(ORG_LIST, echo_columnize_callback, owner["displayName"], owner["key"])
                        + "\n"
                    )
            else:
                print(_("{username} cannot register with any organizations.").format(username=self.username))

        except connection.RestlibException as re:
            log.exception(re)
            log.error("Error: Unable to retrieve org list from server: {re}".format(re=re))

            system_exit(os.EX_SOFTWARE, re)
        except Exception as e:
            handle_exception(_("Error: Unable to retrieve org list from server"), e)
