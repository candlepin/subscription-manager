#
# Copyright (c) 2010 - 2015 Red Hat, Inc.
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

from subscription_manager.cli import CLI
from smurl.commands import ApiCommand


class SmurlCLI(CLI):

    def __init__(self):
        commands = [ApiCommand]
        CLI.__init__(self, command_classes=commands)

    # default to "api" subcommand
    def _default_command(self):
        cmd = self.cli_commands['api']
        return cmd.main()

    def _find_best_match(self, args):
        """Like the base _find_best_match, but always match at least the default."""
        # argh, CLI is old style class
        cmd = CLI._find_best_match(self, args)
        if not cmd:
            cmd = self.cli_commands['api']
        return cmd
