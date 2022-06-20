from __future__ import print_function, division, absolute_import

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
import contextlib
import logging
import os
import six

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

from rhsmlib.facts import collector
from rhsmlib.facts.dmidecodeparser import DmidecodeParser

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

    def use_dump_file(self, dmidecode):
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
        try:
            import dmidecode
        except ImportError:
            log.warn("Unable to load dmidecode module. No DMI info will be collected")
            raise

        dmiinfo = {}
        try:
            # When alternative memory device file was specified for this class, then
            # try to use it. Otherwise current device file will be used.
            if self.dump_file is not None:
                self.use_dump_file(dmidecode)
            log.debug("Using dmidecode dump file: %s" % dmidecode.get_dev())
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

            for tag, func in list(dmi_data.items()):
                dmiinfo = self._get_dmi_data(func, tag, dmiinfo)
        except Exception as e:
            log.warn(_("Error reading system DMI information: %s"), e, exc_info=True)
        finally:
            self.log_warnings(dmidecode)
        return dmiinfo

    def _read_dmi(self, func):
        try:
            return func()
        except Exception as e:
            log.warn(_("Error reading system DMI information with %s: %s"), func, e)
            return {}

    def _get_dmi_data(self, func, tag, ddict):
        for key, value in list(func.items()):
            for key1, value1 in list(value['data'].items()):
                # FIXME: this loses useful data...
                if not isinstance(value1, six.text_type) and not isinstance(value1, six.binary_type):
                    # we are skipping things like int and bool values, as
                    # well as lists and dicts
                    continue

                # keep track of any cpu socket info we find, we have to do
                # it here, since we flatten it and lose the info creating nkey
                if tag == 'dmi.processor.' and key1 == 'Socket Designation':
                    self._socket_designation.append(value1)

                nkey = ''.join([tag, key1.lower()]).replace(" ", "_")
                ddict[nkey] = six.text_type(value1, 'utf-8')

        # Populate how many socket descriptions we saw in a faux-fact, so we can
        # use it to munge lscpu info later if needed.
        if self._socket_designation:
            ddict['dmi.meta.cpu_socket_count'] = str(len(self._socket_designation))

        return ddict

    def log_warnings(self, dmidecode):
        dmiwarnings = dmidecode.get_warnings()
        if dmiwarnings:
            log.warn(_("Error reading system DMI information: %s"), dmiwarnings, exc_info=True)
            dmidecode.clear_warnings()


class DmidecodeFactCollector(collector.FactsCollector):
    def __init__(self, prefix=None, testing=None, collected_hw_info=None):
        super(DmidecodeFactCollector, self).__init__(
            prefix=prefix, testing=testing, collected_hw_info=collected_hw_info
        )

        self._dmidecode_output = None

    def set_dmidecode_output(self, filename):
        self._dmidecode_output = filename

    def get_all(self):
        """
        Collect facts from the dmidecode output, if available.

        There are different quirks done to make the facts returned closer
        to the way python-dmidecode used to return them.
        """
        parser = DmidecodeParser()
        try:
            if self._dmidecode_output is not None:
                parser.parse_file(self._dmidecode_output)
            else:
                parser.parse()
        except Exception as exc:
            log.warning("Failed to parse the dmidecode output: {exc}")
            log.exception(exc)
            return {}

        dmiinfo = {}
        socket_designations = 0
        # map the various DMI types to the various subtags of "dmi" facts;
        # there can be multiple types for the same subtag, as python-dmidecode
        # aggregated them
        tags = {
            DmidecodeParser.DmiTypes.BIOS_INFORMATION: "dmi.bios.",
            DmidecodeParser.DmiTypes.BIOS_LANGUAGE_INFORMATION: "dmi.bios.",
            DmidecodeParser.DmiTypes.PROCESSOR_INFORMATION: "dmi.processor.",
            DmidecodeParser.DmiTypes.BASEBOARD_INFORMATION: "dmi.baseboard.",
            DmidecodeParser.DmiTypes.SYSTEM_ENCLOSURE_OR_CHASSIS: "dmi.chassis.",
            DmidecodeParser.DmiTypes.SYSTEM_SLOTS: "dmi.slot.",
            DmidecodeParser.DmiTypes.SYSTEM_INFORMATION: "dmi.system.",
            DmidecodeParser.DmiTypes.SYSTEM_CONFIGURATION_OPTIONS: "dmi.system.",
            DmidecodeParser.DmiTypes.MEMORY_DEVICE: "dmi.memory.",
            DmidecodeParser.DmiTypes.PHYSICAL_MEMORY_ARRAY: "dmi.memory.",
            DmidecodeParser.DmiTypes.PORT_CONNECTOR_INFORMATION: "dmi.connector.",
        }
        for dmi_type, facts_tag in tags.items():
            try:
                sections = parser.get_sections(dmi_type)
            except KeyError:
                continue
            # quirk: use the last handle (likely the one with an higher value)
            # in a similar way to what python-dmidecode did
            section = sections[-1]
            for key, value in section.items():
                if not isinstance(value, str):
                    # we are skipping lists
                    continue

                nkey = "".join([facts_tag, key.lower()]).replace(" ", "_")
                nvalue = value
                if nvalue.startswith("0x"):
                    # quirk: hex value, lowercase it like python-dmidecode did
                    nvalue = value.lower()
                elif key == "UUID":
                    # quirk: UUID, uppercase it like python-dmidecode did
                    nvalue = value.upper()
                dmiinfo[nkey] = nvalue

        try:
            sections = parser.get_sections(DmidecodeParser.DmiTypes.PROCESSOR_INFORMATION)
        except KeyError:
            pass
        else:
            socket_designations = sum(1 for s in sections for k in s.keys() if k == "Socket Designation")
            # Populate how many socket descriptions we have in a faux-fact,
            # so we can use it to munge lscpu info later if needed.
            if socket_designations > 0:
                dmiinfo["dmi.meta.cpu_socket_count"] = str(socket_designations)

        try:
            sections = parser.get_sections(DmidecodeParser.DmiTypes.MEMORY_DEVICE)
        except KeyError:
            pass
        else:
            # quirk: set dmi.memory.size based on the first "useful" value
            # among all the memory devices available
            with contextlib.suppress(StopIteration, KeyError):
                dmiinfo["dmi.memory.size"] = next(
                    s["Size"] for s in sections if s["Size"] != "No Module Installed"
                )

        return dmiinfo
