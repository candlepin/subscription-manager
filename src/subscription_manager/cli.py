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
from typing import Dict, List, Optional, Tuple, Type, Union

from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.printing_utils import columnize, echo_columnize_callback
from subscription_manager.i18n_argparse import ArgumentParser
from subscription_manager.utils import print_error

from subscription_manager.i18n import ugettext as _


log = logging.getLogger(__name__)


class InvalidCLIOptionError(Exception):
    def __init__(self, message: str):
        Exception.__init__(self, message)


def flush_stdout_stderr() -> None:
    """
    Try to flush stdout and stderr, when it is not possible
    due to blocking process, then print error message to log file.
    """
    # Try to flush all outputs, see BZ: 1350402
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except IOError as io_err:
        log.error("Error: Unable to print data to stdout/stderr output during exit process: %s" % io_err)


class AbstractCLICommand:
    """
    Base class for rt commands. This class provides a templated run
    strategy.
    """

    def __init__(
        self,
        name: str = "cli",
        aliases: List[str] = None,
        shortdesc: Optional[str] = None,
        primary: bool = False,
    ):
        self.name: str = name
        self.shortdesc: Optional[str] = shortdesc
        self.primary: bool = primary
        self.aliases: List[str] = aliases or []

        self.parser: ArgumentParser = self._create_argparser()

    def main(self, args: Optional[List[str]] = None) -> None:
        raise NotImplementedError("Commands must implement: main(self, args=None)")

    def _validate_options(self) -> None:
        """
        Validates the command's arguments.
        @raise InvalidCLIOptionError: Raised when arg validation fails.
        """
        # No argument validation by default.
        pass

    def _get_usage(self) -> str:
        """
        Usage format strips any leading 'usage' so do not include it.
        """
        return _("%(prog)s {name} [OPTIONS]").format(name=self.name)

    def _do_command(self) -> None:
        """
        Does the work that this command intends.
        """
        raise NotImplementedError("Commands must implement: _do_command(self)")

    def _create_argparser(self) -> ArgumentParser:
        """
        Creates an argparse.ArgumentParser object for this command.

        This is done as separate method so subclasses can provide their own
        ArgumentParser, in case the one provided by this method is not
        sufficient.
        """
        return ArgumentParser(usage=self._get_usage(), description=self.shortdesc)


# taken wholseale from rho...
class CLI:
    def __init__(self, command_classes: List[Type[AbstractCLICommand]] = None):
        command_classes = command_classes or []
        self.cli_commands: Dict[str, AbstractCLICommand] = {}
        self.cli_aliases: Dict[str, AbstractCLICommand] = {}
        for clazz in command_classes:
            cmd: AbstractCLICommand = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_commands[cmd.name] = cmd
                for alias in cmd.aliases:
                    self.cli_aliases[alias] = cmd

    def _add_command(self, cmd: AbstractCLICommand):
        self.cli_commands[cmd.name] = cmd

    def _default_command(self) -> None:
        self._usage()

    def _usage(self) -> None:
        print(_("Usage: %s MODULE-NAME [MODULE-OPTIONS] [--help]") % os.path.basename(sys.argv[0]))
        print("\r")
        items = sorted(self.cli_commands.items())
        items_primary: List[Tuple[str, str]] = []
        items_other: List[Tuple[str, str]] = []

        name: str
        cmd: AbstractCLICommand
        for name, cmd in items:
            if cmd.primary:
                items_primary.append(("  " + name, cmd.shortdesc))
            else:
                items_other.append(("  " + name, cmd.shortdesc))

        all_items: List[Tuple[str, str]] = (
            [(_("Primary Modules:"), "\n")]
            + items_primary
            + [("\n" + _("Other Modules:"), "\n")]
            + items_other
        )
        self._do_columnize(all_items)

    def _do_columnize(self, items_list: List[Tuple[str, str]]) -> None:
        modules, descriptions = list(zip(*items_list))
        print(columnize(modules, echo_columnize_callback, *descriptions) + "\n")

    def _find_best_match(self, args: List[str]) -> Optional[AbstractCLICommand]:
        """
        Returns the subcommand class that best matches the subcommand specified
        in the argument list. For example, if you have two commands that start
        with auth, 'auth show' and 'auth'. Passing in auth show will match
        'auth show' not auth. If there is no 'auth show', it tries to find
        'auth'.

        This function ignores the arguments which begin with --
        """
        possiblecmd: List[str] = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        if not possiblecmd:
            return None

        cmd: Optional[AbstractCLICommand] = None
        i: int = len(possiblecmd)
        while cmd is None:
            key: str = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            cmd = self.cli_commands.get(key)
            if cmd is None:
                cmd = self.cli_aliases.get(key)
            i -= 1

        return cmd

    def main(self) -> Optional[int]:
        cmd: AbstractCLICommand = self._find_best_match(sys.argv)
        if len(sys.argv) < 2:
            self._default_command()
            flush_stdout_stderr()
            sys.exit(0)
        if not cmd:
            self._usage()
            # Allow for a 0 return code if just calling --help
            return_code: int = 1
            if (len(sys.argv) > 1) and (sys.argv[1] == "--help"):
                return_code = 0
            flush_stdout_stderr()
            sys.exit(return_code)

        try:
            return cmd.main()
        except InvalidCLIOptionError as error:
            system_exit(1, error)


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
        print_error(msg)

    # Try to flush all outputs, see BZ: 1350402
    flush_stdout_stderr()

    sys.exit(code)
