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
import os

import rhsm.connection as connection
import subscription_manager.injection as inj

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, handle_exception
from subscription_manager.i18n import ugettext as _


class RedeemCommand(CliCommand):
    def __init__(self):
        shortdesc = _(
            "Deprecated, this command will be removed from the future major releases."
            " This command is no-op in simple content access mode."
            " Attempt to redeem a subscription for a preconfigured system"
        )
        super(RedeemCommand, self).__init__("redeem", shortdesc, False)

        self.parser.add_argument(
            "--email",
            dest="email",
            action="store",
            help=_("email address to notify when " "subscription redemption is complete"),
        )
        self.parser.add_argument(
            "--locale",
            dest="locale",
            action="store",
            help=_(
                "optional language to use for email "
                "notification when subscription redemption is "
                "complete (Examples: en-us, de-de)"
            ),
        )

    def _validate_options(self):
        if not self.options.email:
            system_exit(
                os.EX_USAGE, _("Error: This command requires that you specify an email address with --email.")
            )

    def _do_command(self):
        """
        Executes the command.
        """
        self.assert_should_be_registered()
        self._validate_options()

        try:
            # FIXME: why just facts and package profile update here?
            # update facts first, if we need to
            facts = inj.require(inj.FACTS)
            facts.update_check(self.cp, self.identity.uuid)

            profile_mgr = inj.require(inj.PROFILE_MANAGER)
            profile_mgr.update_check(self.cp, self.identity.uuid)

            # BZ 1248833 Ensure we print out the display message if we get any back
            response = self.cp.activateMachine(self.identity.uuid, self.options.email, self.options.locale)
            if response is None:
                system_exit(os.EX_SOFTWARE, _("Error: Unable to redeem subscription for this system."))
            if response.get("displayMessage"):
                system_exit(0, response.get("displayMessage"))
        except connection.GoneException as ge:
            raise ge
        except connection.RestlibException as e:
            # candlepin throws an exception during activateMachine, even for
            # 200's. We need to look at the code in the RestlibException and proceed
            # accordingly
            if 200 <= e.code <= 210:
                system_exit(0, e)
            else:
                handle_exception("Unable to redeem: {e}".format(e=e), e)
        except Exception as e:
            handle_exception("Unable to redeem: {e}".format(e=e), e)

        self._request_validity_check()
