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
    def __init__(self):
        shortdesc = get_branding().CLI_REGISTER_DEVICE_AUTH

        super().__init__("register_auth", shortdesc, True)
        
        self._add_url_options()
        self.parser.add_argument(
            "--baseurl",
            dest="base_url",
            default=None,
            help=_("base URL for content in form of https://hostname:port/prefix"),
        )
        self.parser.add_argument(
            "--type",
            dest="consumertype",
            default="system",
            metavar="UNITTYPE",
            help=SUPPRESS,
        )
        self.parser.add_argument(
            "--name",
            dest="consumername",
            metavar="SYSTEMNAME",
            help=_("name of the system to register, defaults to the hostname"),
        )
        self.parser.add_argument(
            "--consumerid",
            dest="consumerid",
            metavar="SYSTEMID",
            help=_("the existing system data is pulled from the server"),
        )
        self.parser.add_argument(
            "--org",
            dest="org",
            metavar="ORG_KEY",
            help=_("register with one of multiple organizations for the user, using organization key"),
        )
        self.parser.add_argument(
            "--environments",
            dest="environments",
            help=_(
                "register with a specific environment (single value) or multiple environments "
                "(a comma-separated list) in the destination org. The ability to use multiple "
                "environments is controlled by the entitlement server"
            ),
        )
        self.parser.add_argument(
            "--release",
            dest="release",
            help=_("set a release version"),
        )
        self.parser.add_argument(
            "--autosubscribe",
            action="store_true",
            help=_("Deprecated, see --auto-attach"),
        )
        self.parser.add_argument(
            "--auto-attach",
            action="store_true",
            dest="autoattach",
            help=_("automatically attach compatible subscriptions to this system"),
        )
        self.parser.add_argument(
            "--force",
            action="store_true",
            help=_("include an implicit attempt to unregister before registering a new system identity"),
        )
        self.parser.add_argument(
            "--activationkey",
            action="append",
            dest="activation_keys",
            help=_("activation key to use for registration (can be specified more than once)"),
        )
        self.parser.add_argument(
            "--servicelevel",
            dest="service_level",
            help=_("system preference used when subscribing automatically, requires --auto-attach"),
        )

    def _validate_options(self):
        self.autoattach = self.options.autosubscribe or self.options.autoattach
        if self.is_registered() and not self.options.force:
            system_exit(os.EX_USAGE, _("This system is already registered. Use --force to override"))
        elif self.options.consumername == "":
            system_exit(os.EX_USAGE, _("Error: system name can not be empty."))
        elif (self.options.username or self.options.token) and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys do not require user credentials."))
        elif self.options.consumerid and self.options.activation_keys:
            system_exit(
                os.EX_USAGE, _("Error: Activation keys can not be used with previously registered IDs.")
            )
        elif self.options.environments and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys do not allow environments to be specified."))
        elif self.autoattach and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys cannot be used with --auto-attach."))
        # 746259: Don't allow the user to pass in an empty string as an activation key
        elif self.options.activation_keys and "" in self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Must specify an activation key"))
        elif self.options.service_level and not self.autoattach:
            system_exit(os.EX_USAGE, _("Error: Must use --auto-attach with --servicelevel."))
        elif self.options.activation_keys and not self.options.org:
            system_exit(os.EX_USAGE, _("Error: Must provide --org with activation keys."))
        elif self.options.force and self.options.consumerid:
            system_exit(
                os.EX_USAGE,
                _(
                    "Error: Can not force registration while attempting to recover registration "
                    "with consumerid. Please use --force without --consumerid to re-register or "
                    "use the clean command and try again without --force."
                ),
            )
        # 1485008: allow registration, when --type=RHUI (many of KBase articles describe using RHUI not rhui)
        elif self.options.consumertype and not (
            self.options.consumertype.lower() == "rhui" or self.options.consumertype == "system"
        ):
            system_exit(os.EX_USAGE, _("Error: The --type option has been deprecated and may not be used."))
        if self.options.environments:
            if not self.cp.has_capability(MULTI_ENV) and "," in self.options.environments:
                system_exit(os.EX_USAGE, _("The entitlement server does not allow multiple environments"))

    def _do_command(self):
        """
        Executes the command.
        """

        self.log_client_version()

        # Always warn the user if registered to old RHN/Spacewalk
        if ClassicCheck().is_registered_with_classic():
            print(get_branding().REGISTERED_TO_OTHER_WARNING)

        # self._validate_options()

        # gather installed products info
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)

        if self.is_registered() and self.options.force:
            print("Consumer is already registered, exiting.")
            return

        # Create instance of the OAuth register service class.
        device_auth_service = device_auth.OAuthRegisterService(self.cp, self.cp_provider)
        # Check with candlepin server if device auth is supported.
        auth_capability_data = device_auth_service.get_device_auth_capability()
        # Initialize the device auth process which should return a dictionary if the server supports device auth,
        # otherwise returns None.
        oauth_data = device_auth_service.initialize_device_auth(auth_capability_data)
        if oauth_data is None:
            print("The server does not support OAuth device auth.")
            return
        # Display the oauth login prompt to the user.
        self._display_oauth_login(oauth_data.get("verification_uri"), oauth_data.get("user_code"))
        # Poll the oauth provider until the user has entered a login code.
        access_token = device_auth_service.poll_oauth_provider(auth_capability_data.get("client_id"), oauth_data)
        if access_token:
            print(access_token)
            print("The device has been authorized.")
        else:
            print("The device failed to authorize.")

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
