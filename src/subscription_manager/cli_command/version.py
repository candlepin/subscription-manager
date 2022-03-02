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


class VersionCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Print version information")

        super(VersionCommand, self).__init__("version", shortdesc, False)

    def _do_command(self):
        self.log_server_version()
        print(_("server type: {type}").format(type=self.server_versions["server-type"]))
        print(
            _("subscription management server: {version}").format(version=self.server_versions["candlepin"])
        )
        print(
            _("subscription management rules: {version}").format(
                version=self.server_versions["rules-version"]
            )
        )
        print("subscription-manager: {version}".format(version=self.client_versions["subscription-manager"]))
