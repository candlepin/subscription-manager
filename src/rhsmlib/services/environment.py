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
import logging
from typing import List


from rhsm.connection import UEPConnection

from subscription_manager import injection as inj

log = logging.getLogger(__name__)


class EnvironmentService:
    """
    Class for listing environments
    """

    def __init__(self, cp: UEPConnection) -> None:
        """
        Initialization of EnvironmentService instance
        :param cp: instance of connection?
        """
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.cp = cp

    def list(self, org_id: str, typed_environments: bool = True) -> List[dict]:
        """
        Method for listing environments
        :param org_id: organization to list environments for
        :param typed_environments: Whether output should include typed environments
        :return: List of environments.
        """

        if typed_environments:
            has_typed_environments = self.cp.has_capability("typed_environments")

            if not has_typed_environments:
                log.debug("candlepin does not have typed_environments capability")

            environments = self.cp.getEnvironmentList(org_id, list_all=has_typed_environments)
        else:
            environments = self.cp.getEnvironmentList(org_id)

        return environments
