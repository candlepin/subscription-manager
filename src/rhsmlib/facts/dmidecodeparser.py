# Copyright (c) 2022 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
This module contains a minimal ad-hoc parser for the output of `dmidecode`.

Tailored for the rest of the subscription-manager code, not general enough.
"""

import collections
import contextlib
import enum
import logging
import os
import re
import shutil
import subprocess
from typing import Dict, List, Union, Optional

log = logging.getLogger(__name__)


class DmidecodeParser:
    """
    Simple parser for the dmidecode output.

    This class provides a simple way to parse the output of the dmidecode(1)
    tool, either by running dmidecode(1) directly, or by reading its output
    from a text file.

    This parser only parses the output and collects the various entries,
    so they can be queried as needed.
    """

    @enum.unique
    class DmiTypes(enum.Enum):
        """
        The known DMI types.

        The values represent the actual values in the SMBIOS specification,
        so it possible to use this enum to avoid specifying them when
        looking up sections.
        """

        BIOS_INFORMATION = 0
        SYSTEM_INFORMATION = 1
        BASEBOARD_INFORMATION = 2
        SYSTEM_ENCLOSURE_OR_CHASSIS = 3
        PROCESSOR_INFORMATION = 4
        MEMORY_CONTROLLER_INFORMATION = 5
        MEMORY_MODULE_INFORMATION = 6
        CACHE_INFORMATION = 7
        PORT_CONNECTOR_INFORMATION = 8
        SYSTEM_SLOTS = 9
        ON_BOARD_DEVICES_INFORMATION = 10
        OEM_STRINGS = 11
        SYSTEM_CONFIGURATION_OPTIONS = 12
        BIOS_LANGUAGE_INFORMATION = 13
        GROUP_ASSOCIATIONS = 14
        SYSTEM_EVENT_LOG = 15
        PHYSICAL_MEMORY_ARRAY = 16
        MEMORY_DEVICE = 17
        THIRTYTWO_BIT_MEMORY_ERROR_INFORMATION = 18
        MEMORY_ARRAY_MAPPED_ADDRESS = 19
        MEMORY_DEVICE_MAPPED_ADDRESS = 20
        BUILT_IN_POINTING_DEVICE = 21
        PORTABLE_BATTERY = 22
        SYSTEM_RESET = 23
        HARDWARE_SECURITY = 24
        SYSTEM_POWER_CONTROLS = 25
        VOLTAGE_PROBE = 26
        COOLING_DEVICE = 27
        TEMPERATURE_PROBE = 28
        ELECTRICAL_CURRENT_PROBE = 29
        OUT_OF_BAND_REMOTE_ACCESS = 30
        BOOT_INTEGRITY_SERVICES_ENTRY_POINT = 31
        SYSTEM_BOOT_INFORMATION = 32
        SIXTYFOUR_BIT_MEMORY_ERROR_INFORMATION = 33
        MANAGEMENT_DEVICE = 34
        MANAGEMENT_DEVICE_COMPONENT = 35
        MANAGEMENT_DEVICE_THRESHOLD_DATA = 36
        MEMORY_CHANNEL = 37
        IPMI_DEVICE_INFORMATION = 38
        SYSTEM_POWER_SUPPLY = 39
        ADDITIONAL_INFORMATION = 40
        ONBOARD_DEVICES_EXTENDED_INFORMATION = 41
        MANAGEMENT_CONTROLLER_HOST_INTERFACE = 42
        TPM_DEVICE = 43
        PROCESSOR_ADDITIONAL_INFORMATION = 44

    def __init__(self):
        self._data: Dict[int, Dict[str, Union[str, List[str]]]] = {}
        self._dmi_types = collections.defaultdict(dict)

    def parse(self) -> None:
        """
        Run `dmidecode` and parses its output.

        In case `dmidecode` is not available, cannot be executed, or it exits
        with failure, a warning is logged.
        """
        path: Optional[str] = shutil.which("dmidecode")
        if path is None:
            log.warning("'dmidecode' is not available. No DMI info will be collected.")
            return

        env: Dict[str, str] = dict(os.environ)
        env.update({"LANGUAGE": "en_US.UTF-8"})

        try:
            proc = subprocess.Popen(
                [path], env=env, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self._parse_lines(proc.stdout)
        except subprocess.SubprocessError:
            error: str = proc.stderr.read()
            log.warning(f"Error with dmidecode subprocess: {error}")

    def parse_file(self, filename: str) -> None:
        """
        Parse the output of `dmidecode` previously saved into the specified
        file.
        """
        with open(filename, "r") as f:
            self._parse_lines(f)

    def _parse_lines(self, fd) -> None:
        """
        The actual parsing of the `dmidecode` output.

        'fd' is a file object, so anything where it is possible to read line
        by line (using readline()).
        """

        class ParsingState(enum.Enum):
            """
            Helper enum representing the current state in the parsing.
            """

            NONE = enum.auto()  # not in any section
            IN_SECTION = enum.auto()  # within the header of a section
            IN_RECORD = enum.auto()  # within a record of a section
            IN_BLOCK = enum.auto()  # within a block of a record

        def is_value_specified(possible_value: str) -> bool:
            """
            Is a value actually specified/available?

            This is needed because dmidecode prints "Not Specified"/etc
            instead of omitting a value that is not specified as DMI string
            (le sigh).
            """
            return (
                possible_value != "Not Specified"
                and possible_value != "Not Available"
                and possible_value != "Unknown"
                and possible_value != "Unspecified"
            )

        state: ParsingState = ParsingState.NONE
        current_handle: int = None
        current_key: str = None
        value: str
        # regex to parse the start of a section in the output; example:
        #   Handle 0x0000, DMI type 222, 14 bytes
        re_handle: re.Pattern = re.compile(r"^Handle\s+([^,]+),\s+DMI\s+type\s+(\d+),\s+(\d+)\s+bytes$")

        while True:
            # the output of dmidecode is read and parsed line by line;
            # this is done to avoid reading & keeping in memory the whole
            # output, as it can be big (depending on the available hardware,
            # usually)
            line: str = fd.readline()
            if not line:
                break

            line = line.rstrip()
            # empty line: not in a section
            if len(line) == 0:
                # reset all the state variables, and continue with the next
                # line
                state = ParsingState.NONE
                current_handle = None
                current_key = None
                continue

            # this may be the start of a section
            if line.startswith("Handle "):
                m: re.Match = re_handle.fullmatch(line)
                if m:
                    # it really is a section, so get the various details,
                    # and prepare the internal structures for it
                    state = ParsingState.IN_SECTION
                    current_handle = int(m[1], base=16)
                    current_dmi_type = int(m[2])
                    self._data[current_handle] = dict()
                    handles = self._dmi_types[current_dmi_type].get("handles", [])
                    handles.append(current_handle)
                    self._dmi_types[current_dmi_type]["handles"] = handles
                    continue

            # we are in a section, in particular in the beginning of it
            # (after the "Handle: header): the line is the name of the section,
            # so skip it, and assume that records will follow
            if state == ParsingState.IN_SECTION:
                state = ParsingState.IN_RECORD
                continue

            # we are in a record, or in the block of a record: they are handled
            # in a single case because, since we parse line by line, we cannot
            # know when a block ends (and a new record starts)
            if state == ParsingState.IN_RECORD or state == ParsingState.IN_BLOCK:
                # a block
                if line.startswith("\t\t"):
                    if state == ParsingState.IN_RECORD:
                        # had a value, drop it
                        with contextlib.suppress(KeyError):
                            del self._data[current_handle][current_key]
                    value = line[2:]
                    # if the current record had already a value, turn it into
                    # a list, and append the new value to it; this way, each
                    # line in the block will be a new item in the list which
                    # is the value of this record
                    try:
                        current_value = self._data[current_handle][current_key]
                        if not isinstance(current_value, list):
                            current_value = [current_value]
                        current_value.append(value)
                        self._data[current_handle][current_key] = current_value
                    except KeyError:
                        self._data[current_handle][current_key] = value
                    state = ParsingState.IN_BLOCK
                # a record (and not a block, as that is checked earlier)
                elif line.startswith("\t"):
                    # usually a record is a line e.g.
                    #   Foo: value
                    # so split by the first colon, ignoring potentially
                    # wrong lines
                    parts = line[1:].split(":", maxsplit=1)
                    if len(parts) != 2:
                        continue
                    current_key = parts[0]
                    value = parts[1].lstrip()
                    if is_value_specified(value):
                        self._data[current_handle][current_key] = value
                    state = ParsingState.IN_RECORD

    def get_sections(self, dmi_type: Union[int, DmiTypes]) -> List[Dict[str, Union[str, List[str]]]]:
        """
        Get a list of sections for the specified DMI type.

        'dmi_type' can be either an item of the DmiTypes enum, or the integer
        value of a DMI type.
        """
        if isinstance(dmi_type, self.DmiTypes):
            dmi_type = dmi_type.value

        return [self._data[h] for h in self._dmi_types[dmi_type]["handles"]]

    def get_key(self, dmi_type: Union[int, DmiTypes], key: str) -> Union[str, List[str]]:
        """
        Get the value of a specific key of a specified DMI type.

        In case there are more sections of the specified DMI type, this will
        lookup in the first section printed by dmidecode. This function
        is more or less like a convenience wrapper.

        KeyError is raisen if there is no section of the specified DMI type,
        or that section does not have the specified key.
        """
        values: List[Dict[str, Union[str, List[str]]]] = self.get_sections(dmi_type)
        return values[0][key]
