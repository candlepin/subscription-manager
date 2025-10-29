# Copyright (c) 2023 Red Hat, Inc.
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
import os
import re
from typing import Callable, Dict, List, Union

from rhsmlib.facts import collector

log = logging.getLogger(__name__)


class DiskCollector(collector.FactsCollector):
    def __init__(
        self,
        arch: str = None,
        prefix: str = None,
        testing: bool = None,
        collected_hw_info: Dict[str, Union[str, int, bool, None]] = None,
    ):
        super().__init__(arch=arch, prefix=prefix, testing=testing, collected_hw_info=None)

        self.hardware_methods: List[Callable] = [
            self.get_disk_size_info,
        ]

    def _get_block_devices(self) -> List[str]:
        """Get list of block devices from /sys/block/"""
        block_devices: List[str] = []
        sys_block_path: str = self.prefix + "/sys/block"

        try:
            if os.path.exists(sys_block_path):
                for device in os.listdir(sys_block_path):
                    # Skip loop devices, ram devices, and other virtual devices
                    # Focus on actual disk devices (sd*, vd*, nvme*, hd*, xvd*)
                    if re.match(r'^(sd[a-z]+|vd[a-z]+|nvme[0-9]+n[0-9]+|hd[a-z]+|xvd[a-z]+)$', device):
                        block_devices.append(device)
        except OSError as e:
            log.debug(f"Could not read /sys/block directory: {e}")

        return sorted(block_devices)

    def _get_device_size_bytes(self, device: str) -> int:
        """Get the size of a block device in bytes"""
        size_file: str = f"{self.prefix}/sys/block/{device}/size"
        try:
            with open(size_file, 'r') as f:
                # The size file contains the number of 512-byte sectors
                sectors = int(f.read().strip())
                return sectors * 512
        except (OSError, ValueError) as e:
            log.debug(f"Could not read size for device {device}: {e}")
            return 0

    def get_disk_size_info(self) -> Dict[str, Union[str, int]]:
        """Get disk size information for all block devices.

        Resulting facts have 'disk.<device_name>.size_bytes' format.
        """
        result: Dict[str, Union[str, int]] = {}

        block_devices = self._get_block_devices()

        for device in block_devices:
            size_bytes = self._get_device_size_bytes(device)
            if size_bytes > 0:
                result[f"disk.{device}.size_bytes"] = size_bytes

        return result