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

"""
This module contains minimalistic collectors of system facts
"""

# TODO: Create some service for gathering system facts that could be
# TODO: used by many applications on Linux.

import os
import shutil
import subprocess
import logging

log = logging.getLogger(__name__)


class MiniHostCollector:
    """
    Minimalistic collector of host facts
    """

    VIRT_WHAT_PATH = "/usr/sbin/virt-what"
    DMIDECODE_PATH = "/usr/sbin/dmidecode"

    def get_virt_what(self) -> dict:
        """
        Try to call virt-what and parse output from this application
        :return: dictionary with facts
        """

        if os.path.isfile(self.VIRT_WHAT_PATH) is False:
            log.error(f"The {self.VIRT_WHAT_PATH} does not exists")
            return {}

        try:
            output = subprocess.check_output(self.VIRT_WHAT_PATH)
        except Exception as err:
            log.error(f"Failed to call {self.VIRT_WHAT_PATH}: {err}")
            return {}

        if isinstance(output, bytes):
            output = output.decode("utf-8")

        virt_dict = {}

        host_type = ", ".join(output.splitlines())

        # If this is blank, then system is not a guest
        virt_dict["virt.is_guest"] = bool(host_type)

        if virt_dict["virt.is_guest"] is True:
            virt_dict["virt.host_type"] = host_type
        else:
            virt_dict["virt.host_type"] = "Not Applicable"

        return virt_dict

    def _get_dmidecode_string(self, string_keyword):
        """
        Run `dmidecode` to get the value of a specific DMI string.

        :return: string with DMI value, or None on error
        """
        env = dict(os.environ)
        env.update({"LANGUAGE": "en_US.UTF-8"})

        args = [self.DMIDECODE_PATH, "-s", string_keyword]

        try:
            res = subprocess.check_output(args, stderr=subprocess.PIPE, universal_newlines=True)
        except subprocess.SubprocessError as exc:
            log.error(f"Failed to call '{' '.join(args)}': {exc}")
            return None

        return res.rstrip()

    def get_dmidecode(self) -> dict:
        """
        Try to get output from dmidecode. It requires the dmidecode tool
        :return: Dictionary with facts
        """
        if shutil.which(self.DMIDECODE_PATH) is None:
            log.error("The dmidecode executable is not installed. Unable to detect public cloud providers.")
            return {}

        # DMI strings required, and that can provide hits for detection
        dmi_tags = {
            "dmi.baseboard.manufacturer": "baseboard-manufacturer",
            "dmi.bios.vendor": "bios-vendor",
            "dmi.bios.version": "bios-version",
            "dmi.chassis.asset_tag": "chassis-asset-tag",
            "dmi.chassis.manufacturer": "chassis-manufacturer",
            "dmi.chassis.serial_number": "chassis-serial-number",
            "dmi.chassis.version": "chassis-version",
            "dmi.system.manufacturer": "system-manufacturer",
            "dmi.system.serial_number": "system-serial-number",
            "dmi.system.uuid": "system-uuid",
        }

        dmi_info = {}
        for tag, string_keyword in dmi_tags.items():
            value = self._get_dmidecode_string(string_keyword)
            if value is not None:
                dmi_info[tag] = value
        return dmi_info

    def get_all(self) -> dict:
        virt_dict = self.get_virt_what()
        dmidecode_dict = self.get_dmidecode()
        return {**virt_dict, **dmidecode_dict}


# We do not need this collector for cloud-what, so it is really dummy
class MiniCustomFactsCollector:
    @staticmethod
    def get_all() -> dict:
        return {}


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src python3 -m cloud_what.fact_collector
if __name__ == "__main__":
    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    collector = MiniHostCollector()
    facts = collector.get_all()
    print(f">>> debug <<<< {facts}")
