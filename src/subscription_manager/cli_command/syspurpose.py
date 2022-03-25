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
import json
import logging
import os
import sys

from rhsm import connection

from subscription_manager import syspurposelib
from subscription_manager.cli_command.addons import AddonsCommand
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.cli_command.role import RoleCommand
from subscription_manager.cli_command.service_level import ServiceLevelCommand
from subscription_manager.cli_command.usage import UsageCommand
from subscription_manager.i18n import ugettext as _

from syspurpose.files import SyncedStore

log = logging.getLogger(__name__)


class SyspurposeCommand(CliCommand):
    """
    Syspurpose command for generic actions. This command will be used for all
    syspurpose actions in the future and it will replace addons, role,
    service-level and usage commands. It will be possible to set service-type
    using this command.

    Note: when the system is not registered, then it doesn't make any sense to
    synchronize syspurpose values with candlepin server, because consumer
    does not exist.
    """

    def __init__(self):
        """
        Initialize the syspurpose command
        """
        short_desc = _("Convenient module for managing all system purpose settings")
        super(SyspurposeCommand, self).__init__("syspurpose", short_desc, primary=False)
        self.parser.add_argument(
            "--show",
            dest="syspurpose_show",
            action="store_true",
            help=_("show current system purpose"),
        )

        # all the subcommands of 'syspurpose'; add them to this list to be
        # registered as such
        syspurpose_command_classes = [AddonsCommand, RoleCommand, ServiceLevelCommand, UsageCommand]
        # create a subparser for all the subcommands: it is passed to all
        # the subcommand classes, so they will create an ArgumentParser that
        # is a child of the 'syspurpose' one, rather than as standalone
        # parsers
        prog = os.path.basename(sys.argv[0])
        subparser = self.parser.add_subparsers(
            # create an own 'prog' string that contains the actual program name
            # followed by this command name; this way, the default 'prog'
            # definition is not used, as it is based on the 'usage' string of
            # the ArgumentParser (self.parser), which contains the '[OPTIONS]'
            # help text (see AbstractCLICommand._get_usage())
            prog=_("{prog} {name}").format(prog=prog, name=self.name),
            dest="subparser_name",
            title=_("Syspurpose submodules"),
            help="",  # trick argparse a bit to not show the {cmd1, cmd2, ..}
            metavar="",  # trick argparse a bit to not show the {cmd1, cmd2, ..}
        )
        self.cli_commands = {}
        for clazz in syspurpose_command_classes:
            cmd = clazz(subparser)
            self.cli_commands[cmd.name] = cmd

    def _get_usage(self):
        """
        Reimplemented from AbstractCLICommand to mention the optional submodule
        in the usage string.
        """
        return _("%(prog)s {name} [SUBMODULE] [OPTIONS]").format(name=self.name)

    def _validate_options(self):
        """
        Validate provided options
        :return: None
        """
        # When no CLI options are provided, then show current syspurpose values
        if self.options.syspurpose_show is not True:
            self.options.syspurpose_show = True

    def _do_command(self):
        """
        Own implementation of all actions
        :return: None
        """
        self._validate_options()

        # a subcommand was actually invoked, so dispatch it
        if self.options.subparser_name is not None:
            subcmd = self.cli_commands[self.options.subparser_name]
            # set a reference to ourselves in the subcommand being executed;
            # this way, everything we collected & created in main() is
            # "forwarded" to the subcommand class (see
            # AbstractSyspurposeCommand.__getattr__())
            subcmd.syspurpose_command = self
            subcmd._do_command()
            return

        content = {}
        if self.options.syspurpose_show is True:
            if self.is_registered():
                try:
                    self.cp = self.cp_provider.get_consumer_auth_cp()
                except connection.RestlibException as err:
                    log.exception(err)
                    log.debug("Error: Unable to retrieve system purpose from server")
                except Exception as err:
                    log.debug("Error: Unable to retrieve system purpose from server: {err}".format(err=err))
                else:
                    self.store = SyncedStore(uep=self.cp, consumer_uuid=self.identity.uuid)
                    sync_result = self.store.sync()
                    content = sync_result.result
            else:
                content = syspurposelib.read_syspurpose()
            print(json.dumps(content, indent=2, ensure_ascii=False, sort_keys=True))
