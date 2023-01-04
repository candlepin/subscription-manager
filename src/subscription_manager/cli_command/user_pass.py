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
import errno
import logging
import time

from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.cli import system_exit
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import is_interactive
from rhsmlib.services import device_auth
from rhsm import ourjson as json

log = logging.getLogger(__name__)


class UserPassCommand(CliCommand):
    """
    Abstract class for commands that require a username and password
    """
    DEVICEAUTH_CACHE_FILE = "/var/lib/rhsm/cache/auth_token.json"

    def __init__(self, name, shortdesc=None, primary=False):
        super(UserPassCommand, self).__init__(name, shortdesc, primary)
        self._username = None
        self._password = None
        self._token = None

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
        self.parser.add_argument(
            "--no-token-reuse",
            dest="no_token_reuse",
            action='store_true',
            help=_("prevents the access token from being reused when authorizing against the server")
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

    def check_device_auth_cache(self):
        """
        Checks if an authorization token is passed to the command, and if not
        attempts to retrieve the authorization token from a cache file. If the token in the cache file
        has expired or does not exist then the OAuth device auth process is started.

        The device auth process displays a verification url and access code that the user must enter
        in a browser on a separate device. The service will poll the OAuth provider until an access code is
        entered and then retrieves the authorization token and stores it in a cache file.
        """
        if self.options.token:
            self._token = self.options.token
        elif not self._token:
            if not self.options.no_token_reuse:
                cached_token = self.__read_cache_file(self.DEVICEAUTH_CACHE_FILE)
                if cached_token is not None:
                    if cached_token["expires"] - int(time.time()) > 0:
                        self._token = cached_token["token"]
                        print(_("Reusing access token from cache. Token reuse can be disabled by passing the --no-token-reuse option"))
                        return
                    else:
                        log.debug("Device access token expired")
                        self.__delete_cache_file(self.DEVICEAUTH_CACHE_FILE)
                        log.debug("Device access token cache deleted.")
                        print(_("Device access token cache deleted."))
            if self.cp.has_capability("device_auth"):
                admin_cp = self.cp_provider.get_no_auth_cp()
                device_auth_service = device_auth.OAuthRegisterService(admin_cp)

                # Initialize device auth service and display the verification url and access code.
                oauth_data = device_auth_service.initialize_device_auth()
                self.display_oauth_login(oauth_data.get("verification_uri"), oauth_data.get("user_code"))
                # Poll the OAuth provider until the access code is entered and retrieve the token.
                oauth_access_data = device_auth_service.poll_oauth_provider(oauth_data)

                # Save the token and its expiration timestamp to a cache file.
                self._token = str(oauth_access_data["access_token"])
                token_created_timestamp = int(time.time())
                token_expires_timestamp = token_created_timestamp + int(oauth_access_data["expires_in"])
                print("Access Token: " + self._token)
                print("Token Expires In: " + str(oauth_access_data["expires_in"]))
                cache_data = {
                    "token": self._token,
                    "expires": token_expires_timestamp,
                }
                self.__write_cache_file(cache_data, self.DEVICEAUTH_CACHE_FILE)

    def __read_cache_file(self, file_name):
        try:
            with open(file_name) as file:
                json_str = file.read()
                data = json.loads(json_str)
            return data
        except IOError as err:
            # if the file does not exist we'll create it later
            if err.errno != errno.ENOENT:
                log.error("Unable to read access token cache: %s" % file_name)
                log.exception(err)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass
        return None

    def __write_cache_file(self, data, file_name):
        try:
            dir_name = os.path.dirname(file_name)
            if not os.access(dir_name, os.R_OK):
                log.debug("Try to create directory: %s" % dir_name)
                os.makedirs(dir_name)
            with open(file_name, "w") as file:
                json.dump(data, file, default=json.encode)
            log.debug("Wrote access token cache: %s" % file_name)
        except IOError as err:
            log.error("Unable to write access token cache: %s" % file_name)
            log.exception(err)

    def __delete_cache_file(self, file_name):
        if os.path.exists(file_name):
            log.debug("Deleting access token cache: %s" % file_name)
            os.remove(file_name)

    def display_oauth_login(self, verification_uri: str, user_code: str):
        if verification_uri is None:
            raise ValueError("Error: A verification uri must be provided to display in the oauth login message.")
        if user_code is None:
            raise ValueError("Error: A oauth user login code must be provided to display in the oauth login message.")
        # This implementation currently only displays the verification uri and login code
        # and can be expanded to display a QR code.
        print(_("Using a browser on another device, visit:\n{verification_uri}\nAnd enter the following code to log in:\n'{user_code}'").format(
            verification_uri=verification_uri,
            user_code=user_code
        ))

    # lazy load the username and password, prompting for them if they weren't
    # given as options. this lets us not prompt if another option fails,
    # or we don't need them.
    @property
    def username(self):
        if not self._username:
            if self.token:
                self._username = self.cp_provider.token_username
                return self._username
            (self._username, self._password) = self._get_username_and_password(
                self.options.username, self.options.password
            )
        return self._username

    @property
    def password(self):
        if not self._password and not self.token:
            (self._username, self._password) = self._get_username_and_password(
                self.options.username, self.options.password
            )
        return self._password

    @property
    def token(self):
        if not self._token:
            self.check_device_auth_cache()
        return self._token
