from __future__ import print_function, division, absolute_import

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
import os
import sys
import logging
from typing import Union

import six

from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.printing_utils import columnize, echo_columnize_callback
from subscription_manager.i18n_argparse import ArgumentParser
from subscription_manager.utils import print_error

from subscription_manager.i18n import ugettext as _


log = logging.getLogger(__name__)


class InvalidCLIOptionError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


def flush_stdout_stderr():
    """
    Try to flush stdout and stderr, when it is not possible
    due to blocking process, then print error message to log file.
    :return: None
    """
    # Try to flush all outputs, see BZ: 1350402
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except IOError as io_err:
        log.error("Error: Unable to print data to stdout/stderr output during exit process: %s" % io_err)


class AbstractCLICommand(object):
    """
    Base class for rt commands. This class provides a templated run
    strategy.
    """
    def __init__(self, name="cli", aliases=None, shortdesc=None, primary=False):
        self.name = name
        self.shortdesc = shortdesc
        self.primary = primary
        self.aliases = aliases or []

        self.parser = self._create_argparser()

    def main(self, args=None):
        raise NotImplementedError("Commands must implement: main(self, args=None)")

    def _validate_options(self):
        """
        Validates the command's arguments.
        @raise InvalidCLIOptionError: Raised when arg validation fails.
        """
        # No argument validation by default.
        pass

    def _get_usage(self):
        """
        Usage format strips any leading 'usage' so
        do not include it
        """
        return _("%(prog)s {name} [OPTIONS]").format(name=self.name)

    def _do_command(self):
        """
        Does the work that this command intends.
        """
        raise NotImplementedError("Commands must implement: _do_command(self)")

    def _create_argparser(self):
        """
        Creates an argparse.ArgumentParser object for this command.

        This is done as separate method so subclasses can provide their own
        ArgumentParser, in case the one provided by this method is not
        sufficient.
        """
        return ArgumentParser(usage=self._get_usage(), description=self.shortdesc)


# taken wholseale from rho...
class CLI(object):

    def __init__(self, command_classes=None):
        command_classes = command_classes or []
        self.cli_commands = {}
        self.cli_aliases = {}
        for clazz in command_classes:
            cmd = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_commands[cmd.name] = cmd
                for alias in cmd.aliases:
                    self.cli_aliases[alias] = cmd

    def _add_command(self, cmd):
        self.cli_commands[cmd.name] = cmd

    def _default_command(self):
        self._usage()

    def _usage(self):
        print(_("Usage: %s MODULE-NAME [MODULE-OPTIONS] [--help]") % os.path.basename(sys.argv[0]))
        print("\r")
        items = sorted(self.cli_commands.items())
        items_primary = []
        items_other = []
        for (name, cmd) in items:
            if cmd.primary:
                items_primary.append(("  " + name, cmd.shortdesc))
            else:
                items_other.append(("  " + name, cmd.shortdesc))

        all_items = [(_("Primary Modules:"), '\n')] + \
                items_primary + [('\n' + _("Other Modules:"), '\n')] + \
                items_other
        self._do_columnize(all_items)

    def _do_columnize(self, items_list):
        modules, descriptions = list(zip(*items_list))
        print(columnize(modules, echo_columnize_callback, *descriptions) + '\n')

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
        while cmd is None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            cmd = self.cli_commands.get(key)
            if cmd is None:
                cmd = self.cli_aliases.get(key)
            i -= 1

        return cmd

    def main(self):
        cmd = self._find_best_match(sys.argv)
        if len(sys.argv) < 2:
            self._default_command()
            flush_stdout_stderr()
            sys.exit(0)
        if not cmd:
            self._usage()
            # Allow for a 0 return code if just calling --help
            return_code = 1
            if (len(sys.argv) > 1) and (sys.argv[1] == "--help"):
                return_code = 0
            flush_stdout_stderr()
            sys.exit(return_code)

        try:
            return cmd.main()
        except InvalidCLIOptionError as error:
            print(error)


def system_exit(code: int, msg: Union[str, Exception, None] = None) -> None:
    """
    Exits the process with an exit code and optional message(s).

    :param code: A unix-style system exit code.
    :param msg: A system exit message, a single exception, or none. This parameter defaults to None.
    """

    if msg:
        if isinstance(msg, Exception):
            exception_mapper: ExceptionMapper = ExceptionMapper()
            msg = exception_mapper.get_message(msg)
        if isinstance(msg, six.text_type) and six.PY2:
            print_error(msg.encode("utf8"))
        else:
            print_error(msg)

    # Try to flush all outputs, see BZ: 1350402
    flush_stdout_stderr()

    sys.exit(code)
