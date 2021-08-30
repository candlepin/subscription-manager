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
from subscription_manager.cli_command.org import OrgCommand
from subscription_manager.cli_command.list import ENVIRONMENT_LIST
from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.i18n import ugettext as _
from subscription_manager.printing_utils import columnize, echo_columnize_callback
from subscription_manager.utils import get_supported_resources

log = logging.getLogger(__name__)


class EnvironmentsCommand(OrgCommand):

    def __init__(self):
        shortdesc = _("Display the environments available for a user")
        self._org_help_text = _("specify organization for environment list, using organization key")

        super(EnvironmentsCommand, self).__init__("environments", shortdesc,
                                                  False)
        self._add_url_options()

    def _get_environments(self, org):
        return self.cp.getEnvironmentList(org)

    def _do_command(self):
        self._validate_options()
        try:
            if self.options.token:
                self.cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
            else:
                self.cp_provider.set_user_pass(self.username, self.password)
                self.cp = self.cp_provider.get_basic_auth_cp()
            supported_resources = get_supported_resources()
            if 'environments' in supported_resources:
                environments = self._get_environments(self.org)

                if len(environments):
                    print("+-------------------------------------------+")
                    print("          {env}".format(env=_('Environments')))
                    print("+-------------------------------------------+")
                    for env in environments:
                        print(columnize(ENVIRONMENT_LIST, echo_columnize_callback, env['name'],
                                        env['description'] or "") + "\n")
                else:
                    print(_("This org does not have any environments."))
            else:
                system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support environments."))

            log.debug("Successfully retrieved environment list from server.")
        except connection.RestlibException as re:
            log.exception(re)
            log.error("Error: Unable to retrieve environment list from server: {re}".format(re=re))

            mapped_message: str = ExceptionMapper().get_message(re)
            system_exit(os.EX_SOFTWARE, mapped_message)
        except Exception as e:
            handle_exception(_("Error: Unable to retrieve environment list from server"), e)
