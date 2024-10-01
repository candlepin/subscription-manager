# Copyright (c) 2024 Red Hat, Inc.
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
import logging
from typing import List


from rhsm.connection import UEPConnection

log = logging.getLogger(__name__)


class EnvironmentService:
    """
    Class for using environments
    """

    def __init__(self, cp: UEPConnection) -> None:
        """
        Initialization of EnvironmentService instance
        :param cp: connection to Candlepin
        """
        self.cp = cp

    def list(self, org_id: str) -> List[dict]:
        """
        Method for listing environments
        :param org_id: organization to list environments for
        :return: List of environments.
        """
        list_all = self.cp.has_capability("typed_environments")
        environments = self.cp.getEnvironmentList(org_id, list_all=list_all)

        return environments
