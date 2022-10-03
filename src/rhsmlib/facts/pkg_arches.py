# Copyright (c) 2020 ATIX AG
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
import subprocess
from typing import Dict, List, Union

from rhsmlib.facts import collector

log = logging.getLogger(__name__)


class SupportedArchesCollector(collector.FactsCollector):
    """
    Class used for collecting packages architectures of a host
    """

    DEBIAN_DISTRIBUTIONS: List[str] = ["debian", "ubuntu"]

    def __init__(
        self,
        arch: str = None,
        prefix: str = None,
        testing: bool = None,
        collected_hw_info: Dict[str, Union[str, int, bool, None]] = None,
    ):
        super(SupportedArchesCollector, self).__init__(
            arch=arch, prefix=prefix, testing=testing, collected_hw_info=collected_hw_info
        )

    def get_arches_on_debian(self) -> Dict[str, str]:
        """
        Try to return content of all supported packages architectures
        :return: dictionary containing architectures
        Otherwise, a dictionary with an empty string for 'supported_architectures' is returned.
        """
        arches: List[str] = []

        try:
            arch: str = subprocess.check_output(["dpkg", "--print-architecture"]).decode("UTF-8")
            if arch != "":
                arches.append(arch.rstrip("\n"))
        except Exception as e:
            log.error("Error getting dpkg main architecture: %s", e)

        try:
            arch: str = subprocess.check_output(["dpkg", "--print-foreign-architectures"]).decode("UTF-8")
            if arch != "":
                arches.append(arch.rstrip("\n"))
        except Exception as e:
            log.error("Error getting dpkg foreign architecture: %s", e)

        return {"supported_architectures": ",".join(arches)}

    def get_all(self) -> Dict[str, str]:
        """
        Get all architectures of a debian / ubuntu host
        :return: dictionary containing architectures
        """
        arch_info: Dict[str, str] = {}

        dist_name: str = self._collected_hw_info["distribution.name"].lower()
        if any(os in dist_name for os in self.DEBIAN_DISTRIBUTIONS):
            arch_info = self.get_arches_on_debian()

        return arch_info
