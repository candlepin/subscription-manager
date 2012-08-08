#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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

import sys
import os
from subscription_manager.i18n_optparse import OptionParser

import gettext
_ = gettext.gettext


class InvalidCLIOptionError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


# Command classes
class CLICommand(object):
    """
    Base class for rt commands. This class provides a templated run
    strategy.
    """
    def __init__(self, name="cli", short_desc=None):
        self.shortdesc = short_desc
        self.name = name
        self.parser = OptionParser(usage=self._get_usage(), description=self.shortdesc)
        self._define_custom_opts(self.parser)

    def run(self, args=None):
        # Initialize args
        if not args:
            # Skip the program name and the command name.
            args = sys.argv[2:]

        (self.options, self.args) = self.parser.parse_args(args)

        self._validate_options()
        self._run_command()

    def _get_usage(self):
        return _("%%prog %s [OPTIONS]") % self.name

    def _define_custom_opts(self, parser):
        """
        Defines any custom opt args for this command.
        """
        pass

    def _validate_options(self):
        '''
        Validates the command's arguments.
        @raise InvalidCLIOptionError: Raised when arg validation fails.
        '''
        # No argument validation by default.
        pass

    def _run_command(self):
        """
        Does the work that this command intends.
        """
        raise NotImplementedError("Commands must implement: _run_command(self)")


# Taken from rhsm.
class CLI:

    def __init__(self, commands=[]):

        self.cli_commands = {}
        for clazz in commands:
            cmd = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_commands[cmd.name] = cmd

    def _add_command(self, cmd):
        self.cli_commands[cmd.name] = cmd

    def _usage(self):
        print "\n"
        print _("Usage: %s MODULE-NAME [MODULE-OPTIONS] [--help]") % os.path.basename(sys.argv[0])
        print "\n"
        print _("Modules:")
        print "\r"

        items = self.cli_commands.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %s" % (name, cmd.shortdesc))
        print("")

    def _find_best_match(self, args):
        """
        Returns the subcommand class that best matches the subcommand specified
        in the argument list. For example, if you have two commands that start
        with auth, 'auth show' and 'auth'. Passing in auth show will match
        'auth show' not auth. If there is no 'auth show', it tries to find
        'auth'.

        This function ignores the arguments which begin with --
        """
        possiblecmd = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        if not possiblecmd:
            return None

        cmd = None
        i = len(possiblecmd)
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            cmd = self.cli_commands.get(key)
            i -= 1

        return cmd

    def main(self):
        cmd = self._find_best_match(sys.argv)
        if len(sys.argv) < 2 or not cmd:
            self._usage()
            sys.exit(0)

        try:
            return cmd.run()
        except InvalidCLIOptionError, error:
            print error
