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

from mock import patch
from rhsmlib.compat import subprocess_compat as compat
from rhsmlib.facts import virt, firmware_info, collector
from subprocess import CalledProcessError


class HardwareProbeTests(test.fixture.SubManFixture):
    @patch('subprocess.Popen')
    def test_virt_bare_metal(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 0
        hw = virt.VirtCollector()
        expected = {'virt.is_guest': False, 'virt.host_type': 'Not Applicable'}
        self.assertEquals(expected, hw.get_all())

    @patch('subprocess.Popen')
    def test_virt_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 255

        hw = virt.VirtWhatCollector()
        expected = {'virt.is_guest': 'Unknown'}
        self.assertEquals(expected, hw.get_virt_info())

    @patch('subprocess.Popen')
    def test_command_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 2

        # Pick up the mocked class
        self.assertRaises(CalledProcessError, compat.check_output_2_6, 'bad_command')

    @patch('subprocess.Popen')
    def test_command_valid(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['this is valid', None]
        MockPopen.return_value.poll.return_value = 0

        # Pick up the mocked class
        hw = virt.VirtCollector(testing='testing')
        self.assertEquals('this is valid', hw.get_all()['virt.host_type'])

    @patch('subprocess.Popen')
    def test_virt_guest(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['kvm', None]
        MockPopen.return_value.poll.return_value = 0

        hw = virt.VirtCollector()
        expected = {'virt.is_guest': True, 'virt.host_type': 'kvm'}
        self.assertEquals(expected, hw.get_all())

    def test_default_virt_uuid_physical(self):
        """Check that physical systems dont set an 'Unknown' virt.uuid."""
        hw = virt.VirtCollector().get_all()
        hw['virt.host_type'] = 'Not Applicable'
        hw['virt.is_guest'] = False
        self.assertFalse('virt.uuid' in hw)

    def test_default_virt_uuid_guest_no_uuid(self):
        """Check that virt guest systems dont set an 'Unknown' virt.uuid if not found."""
        hw = virt.VirtCollector().get_all()
        hw['virt.host_type'] = 'kvm'
        hw['virt.is_guest'] = True
        self.assertFalse('virt.uuid' in hw)

    def test_default_virt_uuid_guest_with_uuid(self):
        """Check that virt guest systems don't set an 'Unknown' virt.uuid if virt.uuid is found."""
        fake_virt_uuid = {'dmi.system.uuid': 'this-is-a-weird-uuid'}
        hw = virt.VirtCollector(collected_hw_info=fake_virt_uuid).get_all()
        hw['virt.host_type'] = 'kvm'
        hw['virt.is_guest'] = True
        self.assertTrue('virt.uuid' in hw)
        self.assertEquals(fake_virt_uuid['dmi.system.uuid'], hw['virt.uuid'])

    def test_get_arch(self):
        import platform
        self.assertEquals(platform.machine(), collector.get_arch())

    def test_get_platform_specific_info_provider(self):
        import platform
        info_provider = firmware_info.get_firmware_collector(arch=platform.machine())
        self.assertTrue(info_provider is not None)

    @patch("rhsmlib.facts.collector.get_arch")
    def test_get_platform_specific_info_provider_not_dmi(self, mock_get_arch):
        info_provider = firmware_info.get_firmware_collector("s390x")
        self.assertIsInstance(info_provider, firmware_info.NullFirmwareInfoCollector)

