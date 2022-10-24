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
import getpass
import readline
import os

from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.cli import system_exit
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import is_interactive


class UserPassCommand(CliCommand):
    """
    Abstract class for commands that require a username and password
    """

    def __init__(self, name, shortdesc=None, primary=False):
        super(UserPassCommand, self).__init__(name, shortdesc, primary)
        self._username = None
        self._password = None

        self.parser.add_argument(
            "--username",
            dest="username",
            help=_("username to use when authorizing against the server"),
        )
        self.parser.add_argument(
            "--password",
            dest="password",
            help=_("password to use when authorizing against the server"),
        )
        self.parser.add_argument(
            "--token",
            dest="token",
            help=_("token to use when authorizing against the server"),
        )

    @staticmethod
    def _get_username_and_password(username, password):
        """
        Safely get a username and password from the tty, without echoing.
        if either username or password are provided as arguments, they will
        not be prompted for. In a non-interactive session, the system exits with an error.
        """
        if not is_interactive():
            if not username:
                system_exit(
                    os.EX_USAGE,
                    _("Error: --username is a required parameter in non-interactive mode."),
                )
            if not password:
                system_exit(
                    os.EX_USAGE,
                    _("Error: --password is a required parameter in non-interactive mode."),
                )

        while not username:
            username = input(_("Username: "))
            readline.clear_history()
        while not password:
            password = getpass.getpass(_("Password: "))
        return username.strip(), password.strip()

    # lazy load the username and password, prompting for them if they weren't
    # given as options. this lets us not prompt if another option fails,
    # or we don't need them.
    @property
    def username(self):
        if not self._username:
            if self.options.token:
                self._username = self.cp_provider.token_username
                return self._username
            (self._username, self._password) = self._get_username_and_password(
                self.options.username, self.options.password
            )
        return self._username

    @property
    def password(self):
        if not self._password and not self.options.token:
            (self._username, self._password) = self._get_username_and_password(
                self.options.username, self.options.password
            )
        return self._password
