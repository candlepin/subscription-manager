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

from rhsmlib.services import entitlement

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, handle_exception
from subscription_manager.i18n import ungettext, ugettext as _
from subscription_manager.utils import unique_list_items

log = logging.getLogger(__name__)


class RemoveCommand(CliCommand):
    def __init__(self):
        super(RemoveCommand, self).__init__(self._command_name(), self._short_description(), self._primary())

        self.parser.add_argument(
            "--serial",
            action="append",
            dest="serials",
            metavar="SERIAL",
            help=_("certificate serial number to remove (can be specified more than once)"),
        )
        self.parser.add_argument(
            "--pool",
            action="append",
            dest="pool_ids",
            metavar="POOL_ID",
            help=_("the ID of the pool to remove (can be specified more than once)"),
        )
        self.parser.add_argument(
            "--all",
            dest="all",
            action="store_true",
            help=_("remove all subscriptions from this system"),
        )

    def _short_description(self):
        return _(
            "Deprecated, this command will be removed from the future major releases."
            " This command is no-op in simple content access mode."
            " It tries to remove all or specific subscriptions from this system"
        )

    def _command_name(self):
        return "remove"

    def _primary(self):
        """
        This command is deprecated and no-op. It used to be primary command, but
        there is no reason to have keep this command as primary command anymore.
        """
        return False

    def _validate_options(self):
        if self.options.serials:
            bad = False
            for serial in self.options.serials:
                if not serial.isdigit():
                    print(_("Error: '{serial}' is not a valid serial number").format(serial=serial))
                    bad = True
            if bad:
                system_exit(os.EX_USAGE)
        elif self.options.pool_ids:
            if not self.cp.has_capability("remove_by_pool_id"):
                system_exit(
                    os.EX_UNAVAILABLE,
                    _(
                        "Error: The registered entitlement server does not support remove --pool."
                        "\nInstead, use the remove --serial option."
                    ),
                )
        elif not self.options.all and not self.options.pool_ids:
            system_exit(
                os.EX_USAGE,
                _("Error: This command requires that you specify one of --serial, --pool or --all."),
            )

    def _print_unbind_ids_result(self, success, failure, id_name):
        if success:
            if id_name == "pools":
                print(_("The entitlement server successfully removed these pools:"))
            elif id_name == "serial numbers":
                print(_("The entitlement server successfully removed these serial numbers:"))
            else:
                print(_("The entitlement server successfully removed these IDs:"))
            for id_ in success:
                print("   {id_}".format(id_=id_))
        if failure:
            if id_name == "pools":
                print(_("The entitlement server failed to remove these pools:"))
            elif id_name == "serial numbers":
                print(_("The entitlement server failed to remove these serial numbers:"))
            else:
                print(_("The entitlement server failed to remove these IDs:"))
            for id_ in failure:
                print("   {id_}".format(id_=id_))

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        return_code = 0
        if self.is_registered():
            ent_service = entitlement.EntitlementService(self.cp)
            try:
                if self.options.all:
                    total = ent_service.remove_all_entitlements()
                    # total will be None on older Candlepins that don't
                    # support returning the number of subscriptions unsubscribed from
                    if total is None:
                        print(_("All subscriptions have been removed at the server."))
                    else:
                        count = total["deletedRecords"]
                        print(
                            ungettext(
                                "%s subscription removed at the server.",
                                "%s subscriptions removed at the server.",
                                count,
                            )
                            % count
                        )
                else:
                    # Try to remove subscriptions defined by pool IDs first (remove --pool=...)
                    if self.options.pool_ids:
                        (
                            removed_pools,
                            unremoved_pools,
                            removed_serials,
                        ) = ent_service.remove_entitlements_by_pool_ids(self.options.pool_ids)
                        if not removed_pools:
                            return_code = 1
                        self._print_unbind_ids_result(removed_pools, unremoved_pools, "pools")
                    else:
                        removed_serials = []
                    # Then try to remove subscriptions defined by serials (remove --serial=...)
                    unremoved_serials = []
                    if self.options.serials:
                        serials = unique_list_items(self.options.serials)
                        # Don't remove serials already removed by a pool
                        serials_to_remove = [serial for serial in serials if serial not in removed_serials]
                        _removed_serials, unremoved_serials = ent_service.remove_entitlements_by_serials(
                            serials_to_remove
                        )
                        removed_serials.extend(_removed_serials)
                        if not _removed_serials:
                            return_code = 1
                    # Print final result of removing pools
                    self._print_unbind_ids_result(removed_serials, unremoved_serials, "serial numbers")
            except connection.GoneException as ge:
                raise ge
            except connection.RestlibException as err:
                log.error(err)

                system_exit(os.EX_SOFTWARE, err)
            except Exception as e:
                handle_exception(
                    _("Unable to perform remove due to the following exception: {e}").format(e=e), e
                )
        else:
            # We never got registered, just remove the cert
            try:
                if self.options.all:
                    total = 0
                    for ent in self.entitlement_dir.list():
                        ent.delete()
                        total = total + 1
                    print(
                        ungettext(
                            "{total} subscription removed from this system.",
                            "{total} subscriptions removed from this system.",
                            total,
                        ).format(total=total)
                    )
                else:
                    if self.options.serials or self.options.pool_ids:
                        serials = self.options.serials or []
                        pool_ids = self.options.pool_ids or []
                        count = 0
                        for ent in self.entitlement_dir.list():
                            ent_pool_id = str(getattr(ent.pool, "id", None) or "")
                            if str(ent.serial) in serials or ent_pool_id in pool_ids:
                                ent.delete()
                                print(
                                    _(
                                        "Subscription with serial number {serial} removed from this system"
                                    ).format(serial=str(ent.serial))
                                )
                                count = count + 1
                        if count == 0:
                            return_code = 1
            except Exception as e:
                handle_exception(
                    _("Unable to perform remove due to the following exception: {e}").format(e=e), e
                )

        # it is okay to call this no matter what happens above,
        # it's just a notification to perform a check
        self._request_validity_check()
        return return_code
