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

import rhsm.connection as connection
import subscription_manager.injection as inj

from rhsmlib.facts.hwprobe import ClassicCheck

from subscription_manager import managerlib
from subscription_manager.branding import get_branding
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import handle_exception
from subscription_manager.cli_command.environments import MULTI_ENV
from subscription_manager.cli_command.user_pass import UserPassCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.i18n import ungettext
from subscription_manager.utils import get_current_owner, get_supported_resources

log = logging.getLogger(__name__)


class IdentityCommand(UserPassCommand):
    def __init__(self):
        shortdesc = _("Display the identity certificate for this system or " "request a new one")

        super(IdentityCommand, self).__init__("identity", shortdesc, False)

        self.parser.add_argument(
            "--regenerate",
            action="store_true",
            help=_("request a new certificate be generated"),
        )
        self.parser.add_argument(
            "--force",
            action="store_true",
            help=_(
                "force certificate regeneration (requires username and password); "
                "Only used with --regenerate"
            ),
        )

    def _validate_options(self):
        self.assert_should_be_registered()
        if self.options.force and not self.options.regenerate:
            system_exit(os.EX_USAGE, _("--force can only be used with --regenerate"))
        if (self.options.username or self.options.password) and not self.options.force:
            system_exit(os.EX_USAGE, _("--username and --password can only be used with --force"))
        if self.options.token and not self.options.force:
            system_exit(os.EX_USAGE, _("--token can only be used with --force"))

    def _do_command(self):
        # get current consumer identity
        identity = inj.require(inj.IDENTITY)

        # check for Classic before doing anything else
        if ClassicCheck().is_registered_with_classic():
            if identity.is_valid():
                print(_("server type: {type}").format(type=get_branding().REGISTERED_TO_BOTH_SUMMARY))
            else:
                # no need to continue if user is only registered to Classic
                print(_("server type: {type}").format(type=get_branding().REGISTERED_TO_OTHER_SUMMARY))
                return

        try:
            self._validate_options()
            consumerid = self.identity.uuid
            consumer_name = self.identity.name
            if not self.options.regenerate:
                owner = get_current_owner(self.cp, self.identity)
                ownername = owner["displayName"]
                ownerid = owner["key"]

                print(_("system identity: {consumerid}").format(consumerid=consumerid))
                print(_("name: {consumer_name}").format(consumer_name=consumer_name))
                print(_("org name: {ownername}").format(ownername=ownername))
                print(_("org ID: {ownerid}").format(ownerid=ownerid))

                supported_resources = get_supported_resources(self.cp, self.identity)
                if "environments" in supported_resources:
                    consumer = self.cp.getConsumer(consumerid)
                    evn_key = "environments" if self.cp.has_capability(MULTI_ENV) else "environment"
                    environments = consumer[evn_key]
                    if environments:
                        if evn_key == "environment":
                            environment_names = environments["name"]
                        else:
                            environment_names = ",".join(
                                [environment["name"] for environment in environments]
                            )
                    else:
                        environment_names = _("None")
                    print(
                        ungettext(
                            "environment name: {environment_name}",
                            "environment names: {environment_name}",
                            len(environment_names.split(",")),
                        ).format(environment_name=environment_names)
                    )
            else:
                if self.options.force:
                    # get an UEP with basic auth or keycloak auth
                    if self.options.token:
                        self.cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
                    else:
                        self.cp_provider.set_user_pass(self.username, self.password)
                        self.cp = self.cp_provider.get_basic_auth_cp()
                consumer = self.cp.regenIdCertificate(consumerid)
                managerlib.persist_consumer_cert(consumer)

                # do this in persist_consumer_cert? or some other
                # high level, "I just registered" thing
                self.identity.reload()

                print(_("Identity certificate has been regenerated."))

                log.debug("Successfully generated a new identity from server.")
        except connection.GoneException as ge:
            # Gone exception is caught in CliCommand and a consistent message
            # is printed there for all commands
            raise ge
        except connection.RestlibException as re:
            log.exception(re)
            log.error("Error: Unable to generate a new identity for the system: {re}".format(re=re))

            system_exit(os.EX_SOFTWARE, re)
        except Exception as e:
            handle_exception(_("Error: Unable to generate a new identity for the system"), e)
