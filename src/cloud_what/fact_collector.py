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
import subprocess
import logging

try:
    import dmidecode
except ImportError:
    dmidecode = None

log = logging.getLogger(__name__)


class MiniHostCollector(object):
    """
    Minimalistic collector of host facts
    """

    VIRT_WHAT_PATH = '/usr/sbin/virt-what'

    def get_virt_what(self) -> dict:
        """
        Try to call virt-what and parse output from this application
        :return: dictionary with facts
        """

        if os.path.isfile(self.VIRT_WHAT_PATH) is False:
            log.error(f'The {self.VIRT_WHAT_PATH} does not exists')
            return {}

        try:
            output = subprocess.check_output(self.VIRT_WHAT_PATH)
        except Exception as err:
            log.error(f'Failed to call {self.VIRT_WHAT_PATH}: {err}')
            return {}

        if isinstance(output, bytes):
            output = output.decode('utf-8')

        virt_dict = {}

        host_type = ", ".join(output.splitlines())

        # If this is blank, then system is not a guest
        virt_dict['virt.is_guest'] = bool(host_type)

        if virt_dict['virt.is_guest'] is True:
            virt_dict['virt.host_type'] = host_type
        else:
            virt_dict['virt.host_type'] = "Not Applicable"

        return virt_dict

    def _get_dmi_data(self, func_output, tag, dmi_info):
        for key, value in func_output.items():
            for key1, value1 in list(value['data'].items()):
                # Skip everything that isn't string
                if not isinstance(value1, str) and not isinstance(value1, bytes):
                    continue

                nkey = ''.join([tag, key1.lower()]).replace(" ", "_")
                dmi_info[nkey] = str(value1, 'utf-8')

        return dmi_info

    def get_dmidecode(self) -> dict:
        """
        Try to get output from dmidecode. It require dmidecode module
        :return: Dictionary with facts
        """
        if dmidecode is None:
            log.error('The dmidecode module is not installed. Unable to detect public cloud providers.')
            return {}

        dmi_data = {
            "dmi.bios.": dmidecode.bios,
            "dmi.processor.": dmidecode.processor,
            "dmi.baseboard.": dmidecode.baseboard,
            "dmi.chassis.": dmidecode.chassis,
            "dmi.slot.": dmidecode.slot,
            "dmi.system.": dmidecode.system,
            "dmi.memory.": dmidecode.memory,
            "dmi.connector.": dmidecode.connector,
        }

        dmi_info = {}
        for key, func in dmi_data.items():
            try:
                func_output = func()
            except Exception as err:
                log.error(f'Unable to read system DMI information {func}: {err}')
            else:
                dmi_info = self._get_dmi_data(func_output, key, dmi_info)
        return dmi_info

    def get_all(self) -> dict:
        virt_dict = self.get_virt_what()
        dmidecode_dict = self.get_dmidecode()
        return {**virt_dict, **dmidecode_dict}


# We do not need this collector for cloud-what, so it is really dummy
class MiniCustomFactsCollector(object):
    @staticmethod
    def get_all() -> dict:
        return {}


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src python3 -m cloud_what.fact_collector
if __name__ == '__main__':
    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    collector = MiniHostCollector()
    facts = collector.get_all()
    print(f'>>> debug <<<< {facts}')
