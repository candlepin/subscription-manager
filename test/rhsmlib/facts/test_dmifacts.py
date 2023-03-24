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

from rhsmlib.facts.dmidecodeparser import DmidecodeParser
from rhsmlib.facts.dmiinfo import DmidecodeFactCollector

import contextlib
import os
import unittest


FAKE_PART_NUMBER = "AAAAAAAAAAAAA-ZZ"
FAKE_PRODUCT_NAME = "PPPPPPPPPP"
FAKE_SERIAL_NUMBER = "SSSSSSSS"
FAKE_UUID = "11111111-2222-3333-4444-555555555555"


class DmidecodeTestDataMixin:
    """
    Simple mixin for testing dmidecode output files.
    """

    DATA_SUFFIX = ".txt"

    def __init__(self, *args, **kwargs):
        curdir = os.path.dirname(os.path.realpath(__file__))
        self._datadir = os.path.join(curdir, "dmidecodedata")
        super(DmidecodeTestDataMixin, self).__init__(*args, **kwargs)

    @property
    def datadir(self):
        return self._datadir

    def load_data(self, name):
        name = os.path.join(self.datadir, name)
        parser = DmidecodeParser()
        parser.parse_file(name)
        return parser

    def get_testfiles(self):
        testfiles = []
        with os.scandir(self.datadir) as it:
            for entry in it:
                if not entry.name.endswith(self.DATA_SUFFIX) or not entry.is_file():
                    continue
                testfiles.append(entry.name)
        return testfiles


class TestDmidecodeParser(DmidecodeTestDataMixin, unittest.TestCase):
    def test_data(self):
        testfiles = self.get_testfiles()

        for tf in testfiles:
            with self.subTest(file=tf):
                parser = self.load_data(tf)
                self.assertEqual(
                    parser.get_key(DmidecodeParser.DmiTypes.SYSTEM_INFORMATION, "UUID"), FAKE_UUID
                )
                with contextlib.suppress(KeyError):
                    # not all the systems have a serial number set
                    self.assertEqual(
                        parser.get_key(DmidecodeParser.DmiTypes.SYSTEM_INFORMATION, "Serial Number"),
                        FAKE_SERIAL_NUMBER,
                    )


class TestDmidecodeFactCollector(DmidecodeTestDataMixin, unittest.TestCase):
    # subtags of "dmi" that we expected to be present in the facts
    FACTS_SUBTAGS = [
        "dmi.bios.",
        "dmi.chassis.",
        "dmi.system.",
    ]

    def test_data(self):
        datadir = self.datadir
        testfiles = self.get_testfiles()

        for tf in testfiles:
            with self.subTest(file=tf):
                c = DmidecodeFactCollector()
                c.set_dmidecode_output(os.path.join(datadir, tf))
                facts = c.get_all()
                for subtag in self.FACTS_SUBTAGS:
                    with self.subTest(subtag=subtag):
                        # at least one fact for the specific subtag
                        self.assertTrue(any(f.startswith(subtag) for f in facts))
                self.assertEqual(facts["dmi.system.uuid"], FAKE_UUID)
                with contextlib.suppress(KeyError):
                    # not all the systems have a serial number set
                    self.assertEqual(facts["dmi.system.serial_number"], FAKE_SERIAL_NUMBER)
