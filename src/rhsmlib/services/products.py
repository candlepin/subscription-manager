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
import collections

from subscription_manager import injection as inj
from subscription_manager import utils
from subscription_manager import managerlib


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
        product_status = []

        # It is important to gather data from certificates of installed
        # products at the first time: sorter = inj.require(inj.CERT_SORTER)
        # Data are stored in cache (json file:
        # /var/lib/rhsm/cache/installed_products.json)
        # Calculator use this cache (json file) for assembling request
        # sent to server. When following two lines of code are called in
        # reverse order, then request can be incomplete and result
        # needn't contain all data (especially startDate and endDate).
        # See BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1357152

        # FIXME: make following functions independent on order of calling
        sorter = inj.require(inj.CERT_SORTER)
        calculator = inj.require(inj.PRODUCT_DATE_RANGE_CALCULATOR, self.cp)

        cert_filter = None
        if filter_string:
            cert_filter = utils.ProductCertificateFilter(filter_string)

        # Instead of a dictionary because some legacy methods unpack this as a list
        ProductStatus = collections.namedtuple('ProductStatus',
            ['product_name', 'product_id', 'version', 'arch', 'status', 'status_details', 'starts', 'ends']
        )

        for installed_product in sorted(sorter.installed_products):
            product_cert = sorter.installed_products[installed_product]

            if cert_filter is None or cert_filter.match(product_cert):
                for product in product_cert.products:
                    begin = ""
                    end = ""
                    prod_status_range = calculator.calculate(product.id)

                    if prod_status_range:
                        # Format the date in user's local time as the date
                        # range is returned in GMT.
                        begin = managerlib.format_date(prod_status_range.begin())
                        end = managerlib.format_date(prod_status_range.end())

                    product_status.append(ProductStatus(
                        product.name,
                        installed_product,
                        product.version,
                        ",".join(product.architectures),
                        sorter.get_status(product.id),
                        sorter.reasons.get_product_reasons(product),
                        begin,
                        end
                    ))

        return product_status
