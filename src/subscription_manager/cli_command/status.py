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
import subscription_manager.injection as inj

from rhsm.certificate2 import CONTENT_ACCESS_CERT_TYPE
from rhsm.connection import ConnectionException

from rhsmlib.services import entitlement
from rhsmlib.services.refresh import Refresh

from subscription_manager import syspurposelib
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.printing_utils import format_name
from subscription_manager.utils import is_simple_content_access, get_terminal_width
from time import localtime, strftime

log = logging.getLogger(__name__)


class StatusCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Show status information for this system's subscriptions and products")
        super(StatusCommand, self).__init__("status", shortdesc, True)
        self.parser.add_argument(
            "--ondate",
            dest="on_date",
            help=_("future date to check status on, defaults to today's date (example: {example})").format(
                example=strftime("%Y-%m-%d", localtime())
            ),
        )

    def _get_date_cli_option(self):
        """
        Try to get and validate command line options date
        :return: Return date or None, when date was not provided
        """
        on_date = None
        if self.options.on_date:
            try:
                on_date = entitlement.EntitlementService.parse_date(self.options.on_date)
            except ValueError as err:
                system_exit(os.EX_DATAERR, err)
        return on_date

    def _print_status(self, service_status):
        """
        Print only status
        :return: Print overall status
        """

        print("+-------------------------------------------+")
        print("   " + _("System Status Details"))
        print("+-------------------------------------------+")

        ca_message = ""
        has_cert = _(
            "Content Access Mode is set to Simple Content Access. "
            "This host has access to content, regardless of subscription status.\n"
        )

        certs = self.entitlement_dir.list_with_content_access()
        sca_certs = [cert for cert in certs if cert.entitlement_type == CONTENT_ACCESS_CERT_TYPE]
        sca_mode_detected = False

        refresh_service = Refresh(cp=self.cp, ent_cert_lib=self.entcertlib)

        if sca_certs:
            sca_mode_detected = True
        else:
            # When there are no entitlement SCA certificates, but status_id is "disabled", then
            # it means that content access mode has changed on the server and entitlement certificates
            # have to be refreshed
            if service_status["status_id"] == "disabled":
                refresh_service.refresh()
            if is_simple_content_access(uep=self.cp, identity=self.identity):
                sca_mode_detected = True

        if sca_mode_detected is True:
            # When SCA mode was detected using cache or installed SCA entitlement certificates, but status_id
            # is not "disabled", then it means that content access mode has changed on the server and
            # entitlement certificates have to be refreshed
            status_id = service_status["status_id"]
            if status_id != "disabled":
                log.debug(
                    f"Found SCA cert, but status ID is not 'disabled' ({status_id}). "
                    "Refreshing entitlement certs..."
                )
                refresh_service.refresh()
            else:
                ca_message = has_cert

        print(
            _("Overall Status: {status}\n{message}").format(
                status=service_status["status"], message=ca_message
            )
        )

    def _print_reasons(self, service_status):
        """
        Print reasons for overall status
        :param service_status:
        :return: None
        """
        reasons = service_status["reasons"]

        columns = get_terminal_width()
        for name in reasons:
            print(format_name(name + ":", 0, columns))
            for message in reasons[name]:
                print("- {name}".format(name=format_name(message, 2, columns)))
            print("")

    def _print_syspurpose_status(self, on_date):
        """
        Print syspurpose status
        :return: None
        """
        try:
            store = syspurposelib.get_sys_purpose_store()
            if store:
                store.sync()
        except (OSError, ConnectionException) as ne:
            log.exception(ne)

        syspurpose_cache = inj.require(inj.SYSTEMPURPOSE_COMPLIANCE_STATUS_CACHE)
        syspurpose_cache.load_status(self.cp, self.identity.uuid, on_date)
        print(_("System Purpose Status: {status}").format(status=syspurpose_cache.get_overall_status()))

        syspurpose_status_code = syspurpose_cache.get_overall_status_code()
        if syspurpose_status_code != "matched":
            reasons = syspurpose_cache.get_status_reasons()
            if reasons is not None:
                for reason in reasons:
                    print("- {reason}".format(reason=reason))
        print("")

    def _do_command(self):
        """
        Print status and all reasons it is not valid
        """

        # First get/check if provided date is valid
        on_date = self._get_date_cli_option()

        service_status = entitlement.EntitlementService(cp=self.cp).get_status(on_date)

        self._print_status(service_status)

        self._print_reasons(service_status)

        self._print_syspurpose_status(on_date)

        if service_status["valid"]:
            result = 0
        else:
            result = 1

        return result
