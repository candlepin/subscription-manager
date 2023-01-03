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
import readline
import signal

import rhsm.connection as connection
import subscription_manager.injection as inj

from argparse import SUPPRESS

from rhsm.connection import RemoteServerException
from rhsm.https import ssl
from rhsm.utils import LiveStatusMessage

from rhsmlib.facts.hwprobe import ClassicCheck
from rhsmlib.services import attach, unregister, register, exceptions, device_auth

from subscription_manager import identity
from subscription_manager.branding import get_branding
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import handle_exception, conf
from subscription_manager.cli_command.environments import MULTI_ENV
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.entcertlib import CONTENT_ACCESS_CERT_CAPABILITY
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import (
    restart_virt_who,
    print_error,
    get_supported_resources,
    is_simple_content_access,
    is_interactive,
    is_process_running,
)
from subscription_manager.cli_command.environments import check_set_environment_names

log = logging.getLogger(__name__)


class RegisterAuthCommand(CliCommand):
    def __init__(self, shortdesc=None, primary=False):
        super().__init__("register_auth", shortdesc, primary)

    def _do_command(self):
        """
        Executes the command.
        """

        device_auth_service = device_auth.OAuthRegisterService(self.cp_provider)
        oauth_data = device_auth_service.initialize_device_auth()
        self._display_oauth_login(oauth_data.get("verification_uri"), oauth_data.get("user_code"))
        oauth_access_data = device_auth_service.poll_oauth_provider(oauth_data)  # TODO: make sure this works before continuing
        access_token, expires_in = oauth_access_data["access_token"], oauth_access_data["expires_in"]
        print(access_token, expires_in)

        """
        # Create instance of the OAuth register service class.
        device_auth_service = device_auth.OAuthRegisterService(self.cp, self.cp_provider)
        # Check with candlepin server if device auth is supported.
        auth_capability_data = device_auth_service.get_device_auth_capability()
        print(auth_capability_data)

        # Initialize the device auth process which should return a dictionary if the server supports device auth,
        # otherwise returns None.
        oauth_data = device_auth_service.initialize_device_auth(auth_capability_data)
        if oauth_data is None:
            print("The server does not support OAuth device auth.")
            return

        # Display the oauth login prompt to the user.
        self._display_oauth_login(oauth_data.get("verification_uri"), oauth_data.get("user_code"))

        # Poll the oauth provider until the user has entered a login code.
        access_token = device_auth_service.poll_oauth_provider(auth_capability_data, oauth_data)
        if access_token:
            print(access_token)
            print("The device has been authorized.")
        else:
            print("The device failed to authorize.")
        """
        return None

    def _display_oauth_login(self, verification_uri: str, user_code: str):
        if verification_uri is None:
            raise ValueError("Error: A verification uri must be provided to display in the oauth login message.")
        if user_code is None:
            raise ValueError("Error: A oauth user login code must be provided to display in the oauth login message.")
        # This implementation currently only displays the verification uri and login code
        # and can be expanded to display a QR code.
        print(_("Using a browser on another device, visit:\n{verification_uri}\nAnd enter the following code to log in:\n{user_code}").format(
            verification_uri=verification_uri,
            user_code=user_code
        ))
