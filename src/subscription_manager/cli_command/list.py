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
from rhsmlib.services import products

from subscription_manager.cert_sorter import (
    FUTURE_SUBSCRIBED,
    SUBSCRIBED,
    NOT_SUBSCRIBED,
    EXPIRED,
    PARTIALLY_SUBSCRIBED,
    UNKNOWN,
)

from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _

from subscription_manager.printing_utils import (
    columnize,
    none_wrap_columnize_callback,
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

INSTALLED_PRODUCT_STATUS_SCA = [
    _("Product Name:"),
    _("Product ID:"),
    _("Version:"),
    _("Arch:"),
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
        self.parser.add_argument(
            "--installed",
            action="store_true",
            help=_("list shows those products which are installed (default)"),
        )
        self.parser.add_argument(
            "--matches",
            dest="filter_string",
            help=_("lists only products containing the specified expression in the product information."),
        )

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()

        installed_products = products.InstalledProducts(self.cp).list(self.options.filter_string)

        if len(installed_products):
            print("+-------------------------------------------+")
            print(_("    Installed Product Status"))
            print("+-------------------------------------------+")

            for product in installed_products:
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
            if self.options.filter_string:
                print(
                    _('No installed products were found matching the expression "{filter}".').format(
                        filter=self.options.filter_string
                    )
                )
            else:
                print(_("No installed products to list"))
