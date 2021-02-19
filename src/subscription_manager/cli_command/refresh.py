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
import subscription_manager.injection as inj

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, handle_exception
from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)


class RefreshCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Pull the latest subscription data from the server")

        super(RefreshCommand, self).__init__("refresh", shortdesc, True)

        self.parser.add_option("--force", action='store_true', help=_("force certificate regeneration"))

    def _do_command(self):
        self.assert_should_be_registered()
        try:
            # remove content_access cache, ensuring we get it fresh
            content_access = inj.require(inj.CONTENT_ACCESS_CACHE)
            if content_access.exists():
                content_access.remove()

            if self.options.force is True:
                # get current consumer identity
                consumer_identity = inj.require(inj.IDENTITY)
                # Force a regen of the entitlement certs for this consumer
                if not self.cp.regenEntitlementCertificates(consumer_identity.uuid, True):
                    log.debug("Warning: Unable to refresh entitlement certificates; service likely unavailable")

            self.entcertlib.update()

            log.debug("Refreshed local data")
            print(_("All local data refreshed"))
        except connection.RestlibException as re:
            log.error(re)
            system_exit(os.EX_SOFTWARE, str(re))
        except Exception as e:
            handle_exception(_("Unable to perform refresh due to the following exception: {e}").format(e=e), e)

        self._request_validity_check()
