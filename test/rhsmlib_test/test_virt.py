from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

import test.fixture
from mock import patch, MagicMock

from rhsmlib.facts import virt, firmware_info


class VirtCollectorTest(test.fixture.SubManFixture):
    @patch('subprocess.Popen')
    def test_virt_bare_metal(self, MockPopen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ['', None]
        mock_process.poll.return_value = 0
        mock_process.__enter__.return_value = mock_process
        MockPopen.return_value = mock_process
        hw = virt.VirtCollector()
        expected = {'virt.is_guest': False, 'virt.host_type': 'Not Applicable'}
        self.assertEqual(expected, hw.get_all())

    @patch('subprocess.Popen')
    def test_virt_error(self, MockPopen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ['', None]
        mock_process.poll.return_value = 255
        mock_process.__enter__.return_value = mock_process
        MockPopen.return_value = mock_process

        hw = virt.VirtWhatCollector()
        expected = {'virt.is_guest': 'Unknown'}
        self.assertEqual(expected, hw.get_virt_info())

    @patch('subprocess.Popen')
    def test_command_valid(self, MockPopen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ['this is valid', None]
        mock_process.poll.return_value = 0
        mock_process.__enter__.return_value = mock_process
        MockPopen.return_value = mock_process

        # Pick up the mocked class
        hw = virt.VirtCollector(testing='testing')
        self.assertEqual('this is valid', hw.get_all()['virt.host_type'])

    @patch('subprocess.Popen')
    def test_virt_guest(self, MockPopen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ['kvm', None]
        mock_process.poll.return_value = 0
        mock_process.__enter__.return_value = mock_process
        MockPopen.return_value = mock_process

        hw = virt.VirtCollector()
        expected = {'virt.is_guest': True, 'virt.host_type': 'kvm'}
        self.assertEqual(expected, hw.get_all())

    @patch("rhsmlib.facts.collector.get_arch")
    def test_get_platform_specific_info_provider_not_dmi(self, mock_get_arch):
        info_provider = firmware_info.get_firmware_collector("s390x")
        self.assertIsInstance(info_provider, firmware_info.NullFirmwareInfoCollector)


class VirtUuidCollectorTest(unittest.TestCase):
    def test_strips_null_byte_on_uuid(self):
        with test.fixture.open_mock(content="123\0"):
            collector = virt.VirtUuidCollector(arch='ppc64')
            fact = collector._get_devicetree_vm_uuid()
            self.assertEqual('123', fact['virt.uuid'])

    def test_default_virt_uuid_physical(self):
        """Check that physical systems dont set an 'Unknown' virt.uuid."""
        collected = {
            'virt.host_type': 'Not Applicable',
            'virt.is_guest': False
        }
        result = virt.VirtUuidCollector(collected_hw_info=collected).get_all()
        self.assertFalse('virt.uuid' in result)

    def test_default_virt_uuid_guest_no_uuid(self):
        """Check that virt guest systems dont set an 'Unknown' virt.uuid if not found."""
        collected = {
           'virt.host_type': 'kvm',
           'virt.is_guest': True
        }
        result = virt.VirtUuidCollector(collected_hw_info=collected).get_all()
        self.assertFalse('virt.uuid' in result)

    def test_default_virt_uuid_guest_with_uuid(self):
        """Check that virt guest systems don't set an 'Unknown' virt.uuid if virt.uuid is found."""
        collected = {
            'dmi.system.uuid': 'this-is-a-weird-uuid',
            'virt.host_type': 'kvm',
            'virt.is_guest': True
        }
        result = virt.VirtUuidCollector(collected_hw_info=collected).get_all()
        self.assertTrue('virt.uuid' in result)
        self.assertEqual(collected['dmi.system.uuid'], result['virt.uuid'])
