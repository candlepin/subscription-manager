from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

from subscription_manager import injection as inj
from subscription_manager import productid


class InstalledProducts(object):
    def __init__(self, cp):
        """
        Initialization of InstalledProduct instance.
        :param cp: instance of connection?
        """
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.cp = cp

    def list(self, filter_string=None):
        """
        Method for listening installed products in the system.
        :param filter_string: String for filtering out products.
        :return: List of installed products.
        """
        self.plugin_manager.run(
            "pre_list_installed_products",
            filter_string=filter_string
        )

        response = productid.get_installed_product_status(self.cp, filter_string)

        self.plugin_manager.run(
            "post_list_installed_products",
            filter_string=filter_string,
            installed_products=response
        )

        return response
