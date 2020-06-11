from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import platform
import mock
from test.fixture import open_mock, OPEN_FUNCTION

from rhsmlib.facts import collector, firmware_info
from rhsmlib.facts.firmware_info import UuidFirmwareInfoCollector


class GetArchTest(unittest.TestCase):
    @mock.patch('platform.machine')
    def test_returns_arch(self, mock_machine):
        mock_machine.return_value = "hello_arch"
        arch = collector.get_arch()
        self.assertEqual("hello_arch", arch)

    def test_returns_arch_override(self):
        with open_mock(content="hello_arch"):
            arch = collector.get_arch(prefix="/does/not/exist")
            self.assertEqual("hello_arch", arch)

    def test_get_arch(self):
        self.assertEqual(platform.machine(), collector.get_arch())

    def test_get_platform_specific_info_provider(self):
        info_provider = firmware_info.get_firmware_collector(arch=platform.machine())
        self.assertTrue(info_provider is not None)


class GetNonDmiUuid(unittest.TestCase):
    def test_get_aarch64_firmware_collector(self):
        firmware_provider_class = firmware_info.get_firmware_collector(arch='aarch64')
        self.assertTrue(isinstance(firmware_provider_class, UuidFirmwareInfoCollector))

    @mock.patch(OPEN_FUNCTION, mock.mock_open(read_data="356B6CCC-30C4-11B2-A85C-BBB0CCD29F36"))
    def test_get_aarch64_uuid_collection(self):
        firmware_provider_class = firmware_info.get_firmware_collector(arch='aarch64')
        firmware_provider_class.arch = 'aarch64'
        result = firmware_provider_class.get_all()
        self.assertTrue(result['dmi.system.uuid'] == '356B6CCC-30C4-11B2-A85C-BBB0CCD29F36')

    def test_get_aarch64_uuid_collection_no_file(self):
        mock.mock_open(read_data="no file")
        mock.mock_open.side_effect = IOError()
        firmware_provider_class = firmware_info.get_firmware_collector(arch='aarch64')
        firmware_provider_class.arch = 'aarch64'
        result = firmware_provider_class.get_all()
        self.assertTrue('dmi.system.uuid' not in result)
