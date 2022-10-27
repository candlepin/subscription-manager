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

from rhsmlib.services.refresh import Refresh
import rhsm.connection as connection

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, handle_exception
from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)


class RefreshCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Pull the latest subscription data from the server")
        super(RefreshCommand, self).__init__("refresh", shortdesc, True)
        self.parser.add_argument("--force", action="store_true", help=_("force certificate regeneration"))

    def _do_command(self):
        self.assert_should_be_registered()
        try:
            refresh_service = Refresh(cp=self.cp, ent_cert_lib=self.entcertlib)
            refresh_service.refresh(force=self.options.force)
        except connection.RestlibException as re:
            log.error(re)
            system_exit(os.EX_SOFTWARE, re)
        except Exception as e:
            handle_exception(
                _("Unable to perform refresh due to the following exception: {e}").format(e=e), e
            )
        else:
            print(_("All local data refreshed"))
        self._request_validity_check()
