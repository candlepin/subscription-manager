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

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import (
    handle_exception,
    ERR_NOT_REGISTERED_CODE,
    ERR_NOT_REGISTERED_MSG,
)
from subscription_manager.cli_command.org import OrgCommand
from subscription_manager.cli_command.list import ENVIRONMENT_LIST
from subscription_manager.i18n import ugettext as _
from subscription_manager.i18n import ungettext
from subscription_manager.printing_utils import columnize, echo_columnize_callback
from subscription_manager.utils import get_supported_resources

from subscription_manager.injection import require, IDENTITY


log = logging.getLogger(__name__)
MULTI_ENV = "multi_environment"


class EnvironmentsCommand(OrgCommand):
    def __init__(self):
        shortdesc = _("Display the environments available for a user")
        self._org_help_text = _("specify organization for environment list, using organization key")

        super(EnvironmentsCommand, self).__init__("environments", shortdesc, False)
        self._add_url_options()
        self.parser.add_argument(
            "--set",
            dest="set",
            help=_("set an ordered comma-separated list of environments for this consumer"),
        )
        self.parser.add_argument(
            "--list",
            action="store_true",
            default=False,
            help=_("list all environments for the organization"),
        )
        self.parser.add_argument(
            "--list-enabled",
            action="store_true",
            dest="enabled",
            default=False,
            help=_("list the environments enabled for this consumer in order"),
        )
        self.parser.add_argument(
            "--list-disabled",
            action="store_true",
            dest="disabled",
            default=False,
            help=_("list the environments not enabled for this consumer"),
        )

    def _get_environments(self, org):
        return self.cp.getEnvironmentList(org)

    def _validate_options(self):
        if self.identity.is_valid():
            if self.options.org:
                system_exit(os.EX_USAGE, _("You may not specify an --org for environments when registered."))
        else:
            if self.options.enabled or self.options.disabled:
                system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)

    def _do_command(self):
        self._validate_options()
        supported_resources = get_supported_resources()
        if "environments" not in supported_resources:
            system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support environments."))
        try:
            if self.options.token:
                self.cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
            else:
                if not self.options.enabled:
                    if self.options.username is None or self.options.password is None:
                        print(_("This operation requires user credentials"))
                    self.cp_provider.set_user_pass(self.username, self.password)
                    self.cp = self.cp_provider.get_basic_auth_cp()
            self.identity = require(IDENTITY)
            if self.options.set:
                self._set_environments()
            else:
                self._list_environments()
        except connection.RestlibException as re:
            log.exception(re)
            log.error("Error: Unable to retrieve environment list from server: {re}".format(re=re))

            system_exit(os.EX_SOFTWARE, re)
        except Exception as e:
            handle_exception(_("Error: Unable to retrieve environment list from server"), e)

    def _set_environments(self):
        """
        Updates the environments for the consumer if that is a capability at the server
        """
        if self.cp.has_capability(MULTI_ENV):
            if not self.identity.is_valid():
                system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)
            self.cp.updateConsumer(
                self.identity.uuid,
                environments=self._process_environments(
                    self.cp, self.cp.getOwner(self.identity.uuid)["key"], self.options
                ),
            )
            print(_("Environments updated."))
        else:
            system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support environment updates."))

    def _list_environments(self):
        """
        List the environments based on the option selected in the command line
        enabled/disabled/all
        """
        if not self.cp.has_capability(MULTI_ENV) and (self.options.enabled or self.options.disabled):
            system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support multi-environment operations."))
        environments = []
        if self.options.enabled:
            environments = self.cp.getConsumer(self.identity.uuid)["environments"] or []
        else:
            org_environments = self._get_environments(self.org)
            if self.options.disabled:
                consumer_id_list = []
                for env in self.cp.getConsumer(self.identity.uuid)["environments"]:
                    consumer_id_list.append(env["id"])
                for env in org_environments:
                    if env["id"] not in consumer_id_list:
                        environments.append(env)
            else:
                environments = org_environments

        if len(environments):
            print("+-------------------------------------------+")
            print("          {env}".format(env=_("Environments")))
            print("+-------------------------------------------+")
            for env in environments:
                print(
                    columnize(
                        ENVIRONMENT_LIST,
                        echo_columnize_callback,
                        env["name"],
                        env["description"] or "",
                    )
                    + "\n"
                )
        else:
            print(_("This list operation does not have any environments to report."))

    def _process_environments(self, admin_cp, owner_key, options):
        """
        Gather environment list from server and pass to method to
        validate the environment input against it
        """
        all_env_list = admin_cp.getEnvironmentList(owner_key)
        return check_set_environment_names(all_env_list, options.set)

    @property
    def org(self):
        """
        An override is needed here because we need to use the org from the
        identity for this command if this system is already registered
        """
        self.identity = require(IDENTITY)
        if self.identity.is_valid():
            self._org = self.cp.getOwner(self.identity.uuid)["key"]
            return self._org
        elif self.options.org:
            self._org = self.options.org
            return self._org
        else:
            if not self.options.username:
                self.options.username = self._username
            return super().org


def check_set_environment_names(all_env_list, name_string):
    """
    Checks the environment name(s) input for duplicates and
    inclusion in the full list
    """
    names = [name.strip() for name in name_string.split(",")]
    if len(names) > len(set(names)):
        system_exit(os.EX_DATAERR, _("Error: The same environment may not be listed more than once. "))

    all_names_ids = dict((environment["name"], environment["id"]) for environment in all_env_list)
    missing_names = [name for name in names if name not in all_names_ids.keys()]
    if len(missing_names) > 0:
        msg = ungettext(
            "No such environment: {names}", "No such environments: {names}", len(missing_names)
        ).format(names=", ".join(missing_names))
        system_exit(os.EX_DATAERR, msg)

    return ",".join([all_names_ids[name] for name in names])
