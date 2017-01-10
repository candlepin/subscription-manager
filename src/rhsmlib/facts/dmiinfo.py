# Copyright (c) 2010-2013 Red Hat, Inc.
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
"""Load and collect DMI data.

Note: This module will fail to import if dmidecode fails to import.
      firmware_info.py expects that and handles it, and any other
      module that imports it should handle an import error as well."""

import gettext
import logging
import os

log = logging.getLogger(__name__)

try:
    import dmidecode
except ImportError:
    log.warn("Unable to load dmidecode module. No DMI info will be collected")
    raise

from rhsmlib.facts import collector

_ = gettext.gettext

FIRMWARE_DUMP_FILENAME = "dmi.dump"


class DmiFirmwareInfoCollector(collector.FactsCollector):
    def __init__(self, prefix=None, testing=None, collected_hw_info=None):
        super(DmiFirmwareInfoCollector, self).__init__(
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )

        self._socket_designation = []
        self._socket_counter = 0

        self.dump_file = None
        if testing and prefix:
            self.dump_file = os.path.join(prefix, FIRMWARE_DUMP_FILENAME)
            self.use_dump_file()

    def use_dump_file(self):
        """Set this instances to use a dmidecode dump file.

        WARNING: This involves settings a module global
        attribute in 'dmidecode', not just for this class
        or object, but for the lifetime of the dmidecode module.

        To 'unset' it, it can be set back to '/dev/mem', or
        re set it to another dump file."""
        if os.access(self.dump_file, os.R_OK):
            dmidecode.set_dev(self.dump_file)

    # This needs all of the previously collected hwinfo, so it can decide
    # what is bogus enough that the DMI info is better.
    def get_all(self):
        dmiinfo = {}
        dmi_data = {
            "dmi.bios.": self._read_dmi(dmidecode.bios),
            "dmi.processor.": self._read_dmi(dmidecode.processor),
            "dmi.baseboard.": self._read_dmi(dmidecode.baseboard),
            "dmi.chassis.": self._read_dmi(dmidecode.chassis),
            "dmi.slot.": self._read_dmi(dmidecode.slot),
            "dmi.system.": self._read_dmi(dmidecode.system),
            "dmi.memory.": self._read_dmi(dmidecode.memory),
            "dmi.connector.": self._read_dmi(dmidecode.connector),
        }

        try:
            for tag, func in dmi_data.items():
                dmiinfo = self._get_dmi_data(func, tag, dmiinfo)
        except Exception as e:
            log.warn(_("Error reading system DMI information: %s"), e)

        return dmiinfo

    def _read_dmi(self, func):
        try:
            return func()
        except Exception as e:
            log.warn(_("Error reading system DMI information with %s: %s"), func, e)
            return None

    def _get_dmi_data(self, func, tag, ddict):
        for key, value in func.items():
            for key1, value1 in value['data'].items():
                # FIXME: this loses useful data...
                if not isinstance(value1, str):
                    # we are skipping things like int and bool values, as
                    # well as lists and dicts
                    continue

                # keep track of any cpu socket info we find, we have to do
                # it here, since we flatten it and lose the info creating nkey
                if tag == 'dmi.processor.' and key1 == 'Socket Designation':
                    self._socket_designation.append(value1)

                nkey = ''.join([tag, key1.lower()]).replace(" ", "_")
                ddict[nkey] = str(value1)

        # Populate how many socket descriptions we saw in a faux-fact, so we can
        # use it to munge lscpu info later if needed.
        if self._socket_designation:
            ddict['dmi.meta.cpu_socket_count'] = str(len(self._socket_designation))

        return ddict
