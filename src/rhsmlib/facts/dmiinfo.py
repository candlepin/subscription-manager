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

"""
import contextlib
import logging

log = logging.getLogger(__name__)

from rhsmlib.facts import collector
from rhsmlib.facts.dmidecodeparser import DmidecodeParser


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
