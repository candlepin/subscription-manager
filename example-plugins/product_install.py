from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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
from subscription_manager.base_plugin import SubManPlugin
requires_api_version = "1.0"


class ProductInstallPlugin(SubManPlugin):
    """Plugin triggered when product id certs are installed"""
    name = "product_install"

    def post_product_id_install_hook(self, conduit):
        """`post_product_id_install` hook

        Args:
            conduit: A ProductConduit()
        """
        conduit.log.debug("post product id install called")

        # we need to know what product/product cert
        products = conduit.product_list
        for product in products:
            print("product ", product)

    def pre_product_id_install_hook(self, conduit):
        """pre_product_id_install hook

        Args:
            conduit: A ProductConduit()
        """
        conduit.log.debug("pre product id install called")
