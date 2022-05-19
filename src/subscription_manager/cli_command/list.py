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
import datetime
import logging
import os
import sys

from time import localtime, strftime, strptime

from rhsmlib.services import products, entitlement

from subscription_manager.cert_sorter import (
    FUTURE_SUBSCRIBED,
    SUBSCRIBED,
    NOT_SUBSCRIBED,
    EXPIRED,
    PARTIALLY_SUBSCRIBED,
    UNKNOWN,
)
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.printing_utils import (
    columnize,
    none_wrap_columnize_callback,
    highlight_by_filter_string_columnize_cb,
    echo_columnize_callback,
)
from subscription_manager.utils import is_simple_content_access

# Translates the cert sorter status constants:

STATUS_MAP = {
    FUTURE_SUBSCRIBED: _("Future Subscription"),
    SUBSCRIBED: _("Subscribed"),
    NOT_SUBSCRIBED: _("Not Subscribed"),
    EXPIRED: _("Expired"),
    PARTIALLY_SUBSCRIBED: _("Partially Subscribed"),
    UNKNOWN: _("Unknown"),
}

INSTALLED_PRODUCT_STATUS = [
    _("Product Name:"),
    _("Product ID:"),
    _("Version:"),
    _("Arch:"),
    _("Status:"),
    _("Status Details:"),
    _("Starts:"),
    _("Ends:"),
]

INSTALLED_PRODUCT_STATUS_SCA = [
    _("Product Name:"),
    _("Product ID:"),
    _("Version:"),
    _("Arch:"),
]

AVAILABLE_SUBS_LIST = [
    _("Subscription Name:"),
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Pool ID:"),
    _("Provides Management:"),
    _("Available:"),
    _("Suggested:"),
    _("Service Type:"),
    _("Roles:"),
    _("Service Level:"),
    _("Usage:"),
    _("Add-ons:"),
    _("Subscription Type:"),
    _("Starts:"),
    _("Ends:"),
    _("Entitlement Type:"),
]

AVAILABLE_SUBS_MATCH_COLUMNS = [
    _("Subscription Name:"),
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Service Level:"),
]

REPOS_LIST = [
    _("Repo ID:"),
    _("Repo Name:"),
    _("Repo URL:"),
    _("Enabled:"),
]

PRODUCT_STATUS = [
    _("Product Name:"),
    _("Status:"),
]

ENVIRONMENT_LIST = [
    _("Name:"),
    _("Description:"),
]

ORG_LIST = [
    _("Name:"),
    _("Key:"),
]

OLD_CONSUMED_LIST = [
    _("Subscription Name:"),
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Account:"),
    _("Serial:"),
    _("Pool ID:"),
    _("Provides Management:"),
    _("Active:"),
    _("Quantity Used:"),
    _("Service Type:"),
    _("Service Level:"),
    _("Status Details:"),
    _("Subscription Type:"),
    _("Starts:"),
    _("Ends:"),
    _("System Type:"),
]

CONSUMED_LIST = [
    _("Subscription Name:"),
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Account:"),
    _("Serial:"),
    _("Pool ID:"),
    _("Provides Management:"),
    _("Active:"),
    _("Quantity Used:"),
    _("Service Type:"),
    _("Roles:"),
    _("Service Level:"),
    _("Usage:"),
    _("Add-ons:"),
    _("Status Details:"),
    _("Subscription Type:"),
    _("Starts:"),
    _("Ends:"),
    _("Entitlement Type:"),
]

log = logging.getLogger(__name__)


def show_autosubscribe_output(uep, identity):
    """
    Try to show auto-attach output
    :param uep: object with connection to candlepin
    :param identity: object with identity
    :return: return 1, when all installed products are subscribed, otherwise return 0
    """

    if is_simple_content_access(uep=uep, identity=identity):
        return 0

    installed_products = products.InstalledProducts(uep).list()

    if not installed_products:
        # Returning an error code here breaks registering when no products are installed, and the
        # AttachCommand already performs this check before calling.
        print(_("No products installed."))
        return 0

    log.debug("Attempted to auto-attach/heal the system.")
    print(_("Installed Product Current Status:"))
    subscribed = 1
    all_subscribed = True
    for product in installed_products:
        if product[4] == SUBSCRIBED:
            subscribed = 0
        status = STATUS_MAP[product[4]]
        if product[4] == NOT_SUBSCRIBED:
            all_subscribed = False
        print(columnize(PRODUCT_STATUS, echo_columnize_callback, product[0], status) + "\n")
    if not all_subscribed:
        print(_("Unable to find available subscriptions for all your installed products."))
    return subscribed


class ListCommand(CliCommand):
    def __init__(self):
        shortdesc = _("List subscription and product information for this system")
        super(ListCommand, self).__init__("list", shortdesc, True)
        self.available = None
        self.consumed = None
        self.parser.add_argument(
            "--installed",
            action="store_true",
            help=_("list shows those products which are installed (default)"),
        )
        self.parser.add_argument(
            "--available",
            action="store_true",
            help=_("show those subscriptions which are available"),
        )
        self.parser.add_argument(
            "--all",
            action="store_true",
            help=_("used with --available to ensure all subscriptions are returned"),
        )
        self.parser.add_argument(
            "--ondate",
            dest="on_date",
            help=_(
                "date to search on, defaults to today's date, only used with --available (example: {example})"
            ).format(example=strftime("%Y-%m-%d", localtime())),
        )
        self.parser.add_argument(
            "--consumed",
            action="store_true",
            help=_("show the subscriptions being consumed by this system"),
        )
        self.parser.add_argument(
            "--servicelevel",
            dest="service_level",
            help=_(
                "shows only subscriptions matching the specified service level; "
                "only used with --available and --consumed"
            ),
        )
        self.parser.add_argument(
            "--no-overlap",
            action="store_true",
            help=_(
                "shows pools which provide products that are not already covered; "
                "only used with --available"
            ),
        )
        self.parser.add_argument(
            "--match-installed",
            action="store_true",
            help=_(
                "shows only subscriptions matching products that are currently installed; "
                "only used with --available"
            ),
        )
        self.parser.add_argument(
            "--matches",
            dest="filter_string",
            help=_(
                "lists only subscriptions or products containing the specified expression "
                "in the subscription or product information, varying with the list requested "
                "and the server version (case-insensitive)."
            ),
        )
        self.parser.add_argument(
            "--pool-only",
            dest="pid_only",
            action="store_true",
            help=_(
                "lists only the pool IDs for applicable available or consumed subscriptions; "
                "only used with --available and --consumed"
            ),
        )
        self.parser.add_argument(
            "--afterdate",
            dest="after_date",
            help=_(
                "show pools that are active on or after the given date; "
                "only used with --available (example: {example})"
            ).format(example=strftime("%Y-%m-%d", localtime())),
        )

    def _validate_options(self):
        if self.options.all and not self.options.available:
            system_exit(os.EX_USAGE, _("Error: --all is only applicable with --available"))
        if self.options.on_date and not self.options.available:
            system_exit(os.EX_USAGE, _("Error: --ondate is only applicable with --available"))
        if self.options.service_level is not None and not (self.options.consumed or self.options.available):
            system_exit(
                os.EX_USAGE, _("Error: --servicelevel is only applicable with --available or --consumed")
            )
        if not (self.options.available or self.options.consumed):
            self.options.installed = True
        if not self.options.available and self.options.match_installed:
            system_exit(os.EX_USAGE, _("Error: --match-installed is only applicable with --available"))
        if self.options.no_overlap and not self.options.available:
            system_exit(os.EX_USAGE, _("Error: --no-overlap is only applicable with --available"))
        if self.options.pid_only and self.options.installed:
            system_exit(
                os.EX_USAGE, _("Error: --pool-only is only applicable with --available and/or --consumed")
            )
        if self.options.after_date and not self.options.available:
            system_exit(os.EX_USAGE, _("Error: --afterdate is only applicable with --available"))
        if self.options.after_date and self.options.on_date:
            system_exit(os.EX_USAGE, _("Error: --afterdate cannot be used with --ondate"))

    def _parse_date(self, date):
        """
        Turns a given date into a date object
        :param date: Date string
        :type date: str
        :return: date
        """
        try:
            # doing it this ugly way for pre python 2.5
            return datetime.datetime(*(strptime(date, "%Y-%m-%d")[0:6]))
        except Exception:
            # Translators: dateexample is current date in format like 2014-11-31
            msg = _(
                "Date entered is invalid. Date should be in YYYY-MM-DD format (example: {" "dateexample})"
            )
            dateexample = strftime("%Y-%m-%d", localtime())
            system_exit(os.EX_DATAERR, msg.format(dateexample=dateexample))

    def _split_mulit_value_field(self, values):
        """
        REST API returns multi-value fields in string, where values are separated with comma, but
        each value of multi-value field should be printed on new line. It is done automatically, when
        values are in list
        :param values: String containing multi-value string, where values are separated with comma
        :return: list of values
        """
        if values is None:
            return ""
        return [item.strip() for item in values.split(",")]

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()

        if self.options.installed and not self.options.pid_only:
            installed_products = products.InstalledProducts(self.cp).list(self.options.filter_string)

            if len(installed_products):
                print("+-------------------------------------------+")
                print(_("    Installed Product Status"))
                print("+-------------------------------------------+")

                for product in installed_products:
                    if is_simple_content_access(self.cp, self.identity):
                        print(
                            columnize(
                                INSTALLED_PRODUCT_STATUS_SCA,
                                none_wrap_columnize_callback,
                                product[0],  # Name
                                product[1],  # ID
                                product[2],  # Version
                                product[3],  # Arch
                            )
                            + "\n"
                        )
                    else:
                        status = STATUS_MAP[product[4]]
                        print(
                            columnize(
                                INSTALLED_PRODUCT_STATUS,
                                none_wrap_columnize_callback,
                                product[0],  # Name
                                product[1],  # ID
                                product[2],  # Version
                                product[3],  # Arch
                                status,  # Status
                                product[5],  # Status details
                                product[6],  # Start
                                product[7],  # End
                            )
                            + "\n"
                        )
            else:
                if self.options.filter_string:
                    print(
                        _('No installed products were found matching the expression "{filter}".').format(
                            filter=self.options.filter_string
                        )
                    )
                else:
                    print(_("No installed products to list"))

        if self.options.available:
            self.assert_should_be_registered()
            on_date = None
            after_date = None
            if self.options.on_date:
                on_date = self._parse_date(self.options.on_date)
            elif self.options.after_date:
                after_date = self._parse_date(self.options.after_date)

            epools = entitlement.EntitlementService().get_available_pools(
                show_all=self.options.all,
                on_date=on_date,
                no_overlap=self.options.no_overlap,
                match_installed=self.options.match_installed,
                matches=self.options.filter_string,
                service_level=self.options.service_level,
                after_date=after_date,
            )

            if len(epools):
                if self.options.pid_only:
                    for data in epools:
                        print(data["id"])
                else:
                    print("+-------------------------------------------+")
                    print("    " + _("Available Subscriptions"))
                    print("+-------------------------------------------+")

                    for data in epools:
                        if PoolWrapper(data).is_virt_only():
                            entitlement_type = _("Virtual")
                        else:
                            entitlement_type = _("Physical")

                        if "management_enabled" in data and data["management_enabled"]:
                            data["management_enabled"] = _("Yes")
                        else:
                            data["management_enabled"] = _("No")

                        kwargs = {
                            "filter_string": self.options.filter_string,
                            "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                            "is_atty": sys.stdout.isatty(),
                        }
                        print(
                            columnize(
                                AVAILABLE_SUBS_LIST,
                                highlight_by_filter_string_columnize_cb,
                                data["productName"],
                                data["providedProducts"],
                                data["productId"],
                                data["contractNumber"] or "",
                                data["id"],
                                data["management_enabled"],
                                data["quantity"],
                                data["suggested"],
                                data["service_type"] or "",
                                self._split_mulit_value_field(data["roles"]),
                                data["service_level"] or "",
                                data["usage"] or "",
                                self._split_mulit_value_field(data["addons"]),
                                data["pool_type"],
                                data["startDate"],
                                data["endDate"],
                                entitlement_type,
                                **kwargs
                            )
                            + "\n"
                        )
            elif not self.options.pid_only:
                if self.options.filter_string and self.options.service_level:
                    print(
                        _(
                            "No available subscription pools were found matching the expression "
                            '"{filter}" and the service level "{level}".'
                        ).format(filter=self.options.filter_string, level=self.options.service_level)
                    )
                elif self.options.filter_string:
                    print(
                        _(
                            'No available subscription pools were found matching the expression "{filter}".'
                        ).format(filter=self.options.filter_string)
                    )
                elif self.options.service_level:
                    print(
                        _(
                            'No available subscription pools were found matching the service level "{level}".'
                        ).format(level=self.options.service_level)
                    )
                else:
                    print(_("No available subscription pools to list"))

        if self.options.consumed:
            self.print_consumed(
                service_level=self.options.service_level,
                filter_string=self.options.filter_string,
                pid_only=self.options.pid_only,
            )

    def print_consumed(self, service_level=None, filter_string=None, pid_only=False):
        # list all certificates that have not yet expired, even those
        # that are not yet active.
        service = entitlement.EntitlementService()
        certs = service.get_consumed_product_pools(service_level=service_level, matches=filter_string)

        # Process and display our (filtered) certs:
        if len(certs):
            if pid_only:
                for cert in certs:
                    print(cert.pool_id)
            else:
                print("+-------------------------------------------+")
                print("   " + _("Consumed Subscriptions"))
                print("+-------------------------------------------+")

                for cert in certs:
                    kwargs = {
                        "filter_string": filter_string,
                        "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                        "is_atty": sys.stdout.isatty(),
                    }
                    if hasattr(cert, "roles") and hasattr(cert, "usage") and hasattr(cert, "addons"):
                        print(
                            columnize(CONSUMED_LIST, highlight_by_filter_string_columnize_cb, *cert, **kwargs)
                            + "\n"
                        )
                    else:
                        print(
                            columnize(
                                OLD_CONSUMED_LIST, highlight_by_filter_string_columnize_cb, *cert, **kwargs
                            )
                            + "\n"
                        )
        elif not pid_only:
            if filter_string and service_level:
                print(
                    _(
                        'No consumed subscription pools were found matching the expression "{filter}" '
                        'and the service level "{level}".'
                    ).format(filter=filter_string, level=service_level)
                )
            elif filter_string:
                print(
                    _('No consumed subscription pools were found matching the expression "{filter}".').format(
                        filter=filter_string
                    )
                )
            elif service_level:
                print(
                    _(
                        'No consumed subscription pools were found matching the service level "{level}".'
                    ).format(level=service_level)
                )
            else:
                print(_("No consumed subscription pools were found."))
