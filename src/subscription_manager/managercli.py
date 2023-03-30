# Subscription manager command line utility.
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
import sys

from typing import List, Optional, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from subscription_manager.cli_command.cli import CliCommand

from subscription_manager import managerlib
from subscription_manager.cli import CLI
from subscription_manager.cli_command.addons import AddonsCommand
from subscription_manager.cli_command.attach import AttachCommand
from subscription_manager.cli_command.autoheal import AutohealCommand
from subscription_manager.cli_command.clean import CleanCommand
from subscription_manager.cli_command.config import ConfigCommand
from subscription_manager.cli_command.environments import EnvironmentsCommand
from subscription_manager.cli_command.facts import FactsCommand
from subscription_manager.cli_command.identity import IdentityCommand
from subscription_manager.cli_command.import_cert import ImportCertCommand
from subscription_manager.cli_command.list import ListCommand
from subscription_manager.cli_command.override import OverrideCommand
from subscription_manager.cli_command.owners import OwnersCommand
from subscription_manager.cli_command.plugins import PluginsCommand
from subscription_manager.cli_command.redeem import RedeemCommand
from subscription_manager.cli_command.refresh import RefreshCommand
from subscription_manager.cli_command.register import RegisterCommand
from subscription_manager.cli_command.release import ReleaseCommand
from subscription_manager.cli_command.remove import RemoveCommand
from subscription_manager.cli_command.repos import ReposCommand
from subscription_manager.cli_command.role import RoleCommand
from subscription_manager.cli_command.service_level import ServiceLevelCommand
from subscription_manager.cli_command.status import StatusCommand
from subscription_manager.cli_command.syspurpose import SyspurposeCommand
from subscription_manager.cli_command.unregister import UnRegisterCommand
from subscription_manager.cli_command.usage import UsageCommand
from subscription_manager.cli_command.version import VersionCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.repolib import YumPluginManager

log = logging.getLogger(__name__)


class ManagerCLI(CLI):
    def __init__(self):
        commands: List[Type[CliCommand]] = [
            RegisterCommand,
            UnRegisterCommand,
            AddonsCommand,
            ConfigCommand,
            ListCommand,
            IdentityCommand,
            OwnersCommand,
            RefreshCommand,
            CleanCommand,
            RedeemCommand,
            ReposCommand,
            ReleaseCommand,
            StatusCommand,
            EnvironmentsCommand,
            ImportCertCommand,
            ServiceLevelCommand,
            VersionCommand,
            RemoveCommand,
            AttachCommand,
            PluginsCommand,
            AutohealCommand,
            OverrideCommand,
            RoleCommand,
            UsageCommand,
            FactsCommand,
            SyspurposeCommand,
        ]
        CLI.__init__(self, command_classes=commands)

    def main(self) -> Optional[int]:
        managerlib.check_identity_cert_perms()
        ret: Optional[int] = CLI.main(self)
        # Try to enable all yum plugins (subscription-manager and plugin-id)
        enabled_yum_plugins: List[str] = YumPluginManager.enable_pkg_plugins()
        if len(enabled_yum_plugins) > 0:
            print("\n" + _("WARNING") + "\n\n" + YumPluginManager.warning_message(enabled_yum_plugins) + "\n")
        # Try to close all connections
        managerlib.close_all_connections()
        # Try to flush all outputs, see BZ: 1350402
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except IOError as io_err:
            log.error("Error: Unable to print data to stdout/stderr output during exit process: %s" % io_err)
        return ret


if __name__ == "__main__":
    ManagerCLI().main()
