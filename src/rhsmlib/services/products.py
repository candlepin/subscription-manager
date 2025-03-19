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
from typing import List

from rhsm.connection import UEPConnection

from subscription_manager import injection as inj


class InstalledProducts:
    """
    Class for listing installed products
    """

    def __init__(self, cp: UEPConnection) -> None:
        """
        Initialization of InstalledProduct instance
        :param cp: instance of connection?
        """
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.cp = cp

    def list(self, filter_string: str = None, iso_dates: bool = False) -> List[tuple]:
        """
        Method for listening installed products in the system
        :param filter_string: String for filtering out products
        :param iso_dates: Whether output dates in ISO 8601 format
        :return: List of installed products.
        """
        product_status: List[tuple] = []

        # It is important to gather data from certificates of installed
        # products at the first time: sorter = inj.require(inj.CERT_SORTER)
        # Data are stored in cache (json file:
        # /var/lib/rhsm/cache/installed_products.json)
        # Calculator use this cache (json file) for assembling request
        # sent to server. When following two lines of code are called in
        # reverse order, then request can be incomplete and result
        # needn't contain all data (especially startDate and endDate).
        # See BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1357152

        return product_status
