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
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _

from subscription_manager.printing_utils import (
    columnize,
    none_wrap_columnize_callback,
)

INSTALLED_PRODUCT_STATUS_SCA = [
    _("Product Name:"),
    _("Product ID:"),
    _("Version:"),
    _("Arch:"),
]


log = logging.getLogger(__name__)


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
