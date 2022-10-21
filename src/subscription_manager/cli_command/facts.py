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

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)


class FactsCommand(CliCommand):
    def __init__(self):
        shortdesc = _("View or update the detected system information")
        super(FactsCommand, self).__init__("facts", shortdesc, False)

        self.parser.add_argument(
            "--list",
            action="store_true",
            help=_("list known facts for this system"),
        )
        self.parser.add_argument(
            "--update",
            action="store_true",
            help=_("update the system facts"),
        )

    def _validate_options(self):
        # Only require registration for updating facts
        if self.options.update:
            self.assert_should_be_registered()

        # if no relevant options, default to listing.
        if not (self.options.list or self.options.update):
            self.options.list = True

    def _do_command(self):
        self._validate_options()
        facts = inj.require(inj.FACTS)

        if self.options.list:
            facts_dict = facts.get_facts()
            facts_keys = sorted(facts_dict.keys())

            for key in facts_keys:
                value = facts_dict[key]
                if str(value).strip() == "":
                    value = _("Unknown")
                print("{key}: {value}".format(key=key, value=value))

        if self.options.update:
            identity = inj.require(inj.IDENTITY)
            try:
                facts.update_check(self.cp, identity.uuid, force=True)
            except connection.GoneException as ge:
                raise ge
            except connection.RestlibException as re:
                log.exception(re)

                system_exit(os.EX_SOFTWARE, re)
            log.debug("Succesfully updated the system facts.")
            print(_("Successfully updated the system facts."))
