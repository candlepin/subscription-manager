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
import fileinput
import logging
import os
import re

import rhsm.connection as connection
import subscription_manager.injection as inj

from rhsmlib.services import attach, products

from subscription_manager.action_client import ProfileActionClient, ActionClient
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, handle_exception
from subscription_manager.cli_command.list import show_autosubscribe_output
from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.i18n import ugettext as _
from subscription_manager.packageprofilelib import PackageProfileActionInvoker
from subscription_manager.syspurposelib import save_sla_to_syspurpose_metadata
from subscription_manager.utils import is_simple_content_access, get_current_owner

log = logging.getLogger(__name__)


class AttachCommand(CliCommand):
    def __init__(self):
        super(AttachCommand, self).__init__(self._command_name(), self._short_description(), self._primary())

        self.product = None
        self.substoken = None
        self.auto_attach = True
        self.parser.add_argument(
            "--pool",
            dest="pool",
            action="append",
            help=_("The ID of the pool to attach (can be specified more than once)"),
        )
        self.parser.add_argument(
            "--quantity",
            dest="quantity",
            type=int,
            help=_("Number of subscriptions to attach. May not be used with an auto-attach."),
        )
        self.parser.add_argument(
            "--auto",
            action="store_true",
            help=_(
                "Automatically attach the best-matched compatible subscriptions to this system. "
                "This is the default action."
            ),
        )
        self.parser.add_argument(
            "--servicelevel",
            dest="service_level",
            help=_(
                "Automatically attach only subscriptions matching the specified service level; "
                "only used with --auto"
            ),
        )
        self.parser.add_argument(
            "--file",
            dest="file",
            help=_(
                "A file from which to read pool IDs. If a hyphen is provided, pool IDs will be "
                "read from stdin."
            ),
        )

        # re bz #864207
        _("All installed products are covered by valid entitlements.")
        _("No need to update subscriptions at this time.")

    def _read_pool_ids(self, f):
        if not self.options.pool:
            self.options.pool = []

        for line in fileinput.input(f):
            for pool in filter(bool, re.split(r"\s+", line.strip())):
                self.options.pool.append(pool)

    def _short_description(self):
        return _(
            "Deprecated, this command will be removed from the future major releases. "
            "Attach a specified subscription to the registered system, when system does not use "
            "Simple Content Access mode"
        )

    def _command_name(self):
        return "attach"

    def _primary(self):
        return False

    def _validate_options(self):
        if self.options.pool or self.options.file:
            if self.options.auto:
                system_exit(os.EX_USAGE, _("Error: --auto may not be used when specifying pools."))
            if self.options.service_level:
                system_exit(
                    os.EX_USAGE, _("Error: The --servicelevel option cannot be used when specifying pools.")
                )

        # Quantity must be positive
        if self.options.quantity is not None:
            if self.options.quantity <= 0:
                system_exit(os.EX_USAGE, _("Error: Quantity must be a positive integer."))
            elif self.options.auto or not (self.options.pool or self.options.file):
                system_exit(os.EX_USAGE, _("Error: --quantity may not be used with an auto-attach"))

        # If a pools file was specified, process its contents and append it to options.pool
        if self.options.file:
            self.options.file = os.path.expanduser(self.options.file)
            if self.options.file == "-" or os.path.isfile(self.options.file):
                self._read_pool_ids(self.options.file)

                if len(self.options.pool) < 1:
                    if self.options.file == "-":
                        system_exit(os.EX_DATAERR, _("Error: Received data does not contain any pool IDs."))
                    else:
                        system_exit(
                            os.EX_DATAERR,
                            _('Error: The file "{file}" does not contain any pool IDs.').format(
                                file=self.options.file
                            ),
                        )
            else:
                system_exit(
                    os.EX_DATAERR,
                    _('Error: The file "{file}" does not exist or cannot be read.').format(
                        file=self.options.file
                    ),
                )

    def _print_ignore_attach_message(self):
        """
        Print message about ignoring attach request
        :return: None
        """
        owner = get_current_owner(self.cp, self.identity)
        owner_id = owner["key"]
        print(
            _(
                "Ignoring the request to attach. "
                'Attaching subscriptions is disabled for organization "{owner_id}" '
                "because Simple Content Access (SCA) is enabled."
            ).format(owner_id=owner_id)
        )

    def _do_command(self):
        """
        Executes the command.
        """
        self.assert_should_be_registered()
        self._validate_options()

        # --pool or --file turns off default auto attach
        if self.options.pool or self.options.file:
            self.auto_attach = False

        # Do not try to do auto-attach, when simple content access mode is used
        # BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1826300
        #
        if is_simple_content_access(uep=self.cp, identity=self.identity):
            if self.auto_attach is True:
                self._print_ignore_auto_attach_message()
            else:
                self._print_ignore_attach_message()
            return 0

        installed_products_num = 0
        return_code = 0
        report = None

        # TODO: change to if self.auto_attach: else: pool/file stuff
        try:
            cert_action_client = ActionClient(skips=[PackageProfileActionInvoker])
            cert_action_client.update()
            cert_update = True

            attach_service = attach.AttachService(self.cp)
            if self.options.pool:
                subscribed = False

                for pool in self.options.pool:
                    # odd html strings will cause issues, reject them here.
                    if pool.find("#") >= 0:
                        system_exit(os.EX_USAGE, _("Please enter a valid numeric pool ID."))

                    try:
                        ents = attach_service.attach_pool(pool, self.options.quantity)
                        # Usually just one, but may as well be safe:
                        for ent in ents:
                            pool_json = ent["pool"]
                            print(
                                _("Successfully attached a subscription for: {name}").format(
                                    name=pool_json["productName"]
                                )
                            )
                            log.debug(
                                "Attached a subscription for {name}".format(name=pool_json["productName"])
                            )
                            subscribed = True
                    except connection.RestlibException as re:
                        log.exception(re)

                        exception_mapper = ExceptionMapper()
                        mapped_message = exception_mapper.get_message(re)

                        if re.code == 403:
                            print(mapped_message)  # already subscribed.
                        elif re.code == 400 or re.code == 404:
                            print(mapped_message)  # no such pool.
                        else:
                            system_exit(os.EX_SOFTWARE, mapped_message)  # some other error.. don't try again
                if not subscribed:
                    return_code = 1
            # must be auto
            else:
                installed_products_num = len(products.InstalledProducts(self.cp).list())
                # if we are green, we don't need to go to the server
                self.sorter = inj.require(inj.CERT_SORTER)

                if self.sorter.is_valid():
                    if not installed_products_num:
                        print(_("No Installed products on system. " "No need to attach subscriptions."))
                    else:
                        print(
                            _(
                                "All installed products are covered by valid entitlements. "
                                "No need to update subscriptions at this time."
                            )
                        )
                    cert_update = False
                else:
                    # If service level specified, make an additional request to
                    # verify service levels are supported on the server:
                    if self.options.service_level:
                        consumer = self.cp.getConsumer(self.identity.uuid)
                        if "serviceLevel" not in consumer:
                            system_exit(
                                os.EX_UNAVAILABLE,
                                _(
                                    "Error: The --servicelevel option is not "
                                    "supported by the server. Did not "
                                    "complete your request."
                                ),
                            )

                    attach_service.attach_auto(self.options.service_level)
                    if self.options.service_level is not None:
                        #  RHBZ 1632797 we should only save the sla if the sla was actually
                        #  specified. The uep and consumer_uuid are None, because service_level was sent
                        # to candlepin server using attach_service.attach_auto()
                        save_sla_to_syspurpose_metadata(
                            uep=None, consumer_uuid=None, service_level=self.options.service_level
                        )
                        print(_("Service level set to: {}").format(self.options.service_level))

            if cert_update:
                report = self.entcertlib.update()

            profile_action_client = ProfileActionClient()
            profile_action_client.update()

            if report and report.exceptions():
                print(_("Entitlement Certificate(s) update failed due to the following reasons:"))
                for e in report.exceptions():
                    print("\t-", str(e))
            elif self.auto_attach:
                if not installed_products_num:
                    return_code = 1
                else:
                    self.sorter.force_cert_check()
                    # Make sure that we get fresh status of installed products
                    status_cache = inj.require(inj.ENTITLEMENT_STATUS_CACHE)
                    status_cache.load_status(
                        self.sorter.cp_provider.get_consumer_auth_cp(),
                        self.sorter.identity.uuid,
                        self.sorter.on_date,
                    )
                    self.sorter.load()
                    # run this after entcertlib update, so we have the new entitlements
                    return_code = show_autosubscribe_output(self.cp, self.identity)

        except Exception as e:
            handle_exception("Unable to attach: {e}".format(e=e), e)

        # it is okay to call this no matter what happens above,
        # it's just a notification to perform a check
        self._request_validity_check()

        return return_code
