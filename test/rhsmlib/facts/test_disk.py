# Copyright (c) 2023 Red Hat, Inc.
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

import unittest
import os
import tempfile
from unittest import mock
from unittest.mock import patch, MagicMock

from rhsmlib.facts import disk


class TestDiskCollector(unittest.TestCase):
    def setUp(self):
        self.collector = disk.DiskCollector()

    def test_init(self):
        """Test DiskCollector initialization"""
        self.assertIsInstance(self.collector.hardware_methods, list)
        self.assertEqual(len(self.collector.hardware_methods), 1)
        self.assertEqual(self.collector.hardware_methods[0], self.collector.get_disk_size_info)

    @patch('os.listdir')
    @patch('os.path.exists')
    def test_get_block_devices_no_sys_block(self, mock_exists, mock_listdir):
        """Test _get_block_devices when /sys/block doesn't exist"""
        mock_exists.return_value = False
        result = self.collector._get_block_devices()
        self.assertEqual(result, [])

    @patch('os.listdir')
    @patch('os.path.exists')
    def test_get_block_devices_empty(self, mock_exists, mock_listdir):
        """Test _get_block_devices with empty directory"""
        mock_exists.return_value = True
        mock_listdir.return_value = []
        result = self.collector._get_block_devices()
        self.assertEqual(result, [])

    @patch('os.listdir')
    @patch('os.path.exists')
    def test_get_block_devices_mixed(self, mock_exists, mock_listdir):
        """Test _get_block_devices with mixed device types"""
        mock_exists.return_value = True
        mock_listdir.return_value = [
            'sda',     # Should be included
            'sdb1',    # Should be excluded (partition)
            'vda',     # Should be included
            'nvme0n1', # Should be included
            'loop0',   # Should be excluded
            'ram0',    # Should be excluded
            'dm-0',    # Should be excluded
            'hda',     # Should be included (legacy IDE)
            'xvda',    # Should be included (Xen virtual)
        ]
        result = self.collector._get_block_devices()
        expected = ['hda', 'nvme0n1', 'sda', 'vda', 'xvda']  # sorted
        self.assertEqual(result, expected)

    def test_get_device_size_bytes_missing_file(self):
        """Test _get_device_size_bytes with missing size file"""
        result = self.collector._get_device_size_bytes('nonexistent')
        self.assertEqual(result, 0)

    def test_get_device_size_bytes_invalid_content(self):
        """Test _get_device_size_bytes with invalid file content"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up a temporary sys/block structure
            self.collector.prefix = temp_dir
            device_dir = os.path.join(temp_dir, 'sys', 'block', 'testdev')
            os.makedirs(device_dir)

            size_file = os.path.join(device_dir, 'size')
            with open(size_file, 'w') as f:
                f.write('invalid')

            result = self.collector._get_device_size_bytes('testdev')
            self.assertEqual(result, 0)

    def test_get_device_size_bytes_valid(self):
        """Test _get_device_size_bytes with valid size file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up a temporary sys/block structure
            self.collector.prefix = temp_dir
            device_dir = os.path.join(temp_dir, 'sys', 'block', 'testdev')
            os.makedirs(device_dir)

            size_file = os.path.join(device_dir, 'size')
            sectors = 2048000  # 1 GB in 512-byte sectors
            with open(size_file, 'w') as f:
                f.write(str(sectors))

            result = self.collector._get_device_size_bytes('testdev')
            expected = sectors * 512  # Convert sectors to bytes
            self.assertEqual(result, expected)

    @patch.object(disk.DiskCollector, '_get_device_size_bytes')
    @patch.object(disk.DiskCollector, '_get_block_devices')
    def test_get_disk_size_info(self, mock_get_devices, mock_get_size):
        """Test get_disk_size_info method"""
        mock_get_devices.return_value = ['sda', 'nvme0n1']
        mock_get_size.side_effect = [1000000000000, 500000000000]  # 1TB and 500GB

        result = self.collector.get_disk_size_info()

        expected = {
            'disk.sda.size_bytes': 1000000000000,
            'disk.nvme0n1.size_bytes': 500000000000
        }
        self.assertEqual(result, expected)

    @patch.object(disk.DiskCollector, '_get_device_size_bytes')
    @patch.object(disk.DiskCollector, '_get_block_devices')
    def test_get_disk_size_info_zero_size(self, mock_get_devices, mock_get_size):
        """Test get_disk_size_info filters out zero-size devices"""
        mock_get_devices.return_value = ['sda', 'sdb']
        mock_get_size.side_effect = [1000000000000, 0]  # One valid, one zero

        result = self.collector.get_disk_size_info()

        expected = {
            'disk.sda.size_bytes': 1000000000000
        }
        self.assertEqual(result, expected)

    def test_get_all(self):
        """Test get_all method returns proper dictionary"""
        # Mock the hardware_methods to use our mock function
        mock_method = MagicMock(return_value={'disk.sda.size_bytes': 1000000000000})
        self.collector.hardware_methods = [mock_method]

        result = self.collector.get_all()

        self.assertIsInstance(result, dict)
        self.assertEqual(result, {'disk.sda.size_bytes': 1000000000000})
        mock_method.assert_called_once()

    def test_collect(self):
        """Test collect method returns FactsCollection"""
        with patch.object(self.collector, 'get_all') as mock_get_all:
            mock_get_all.return_value = {'disk.sda.size_bytes': 1000000000000}

            result = self.collector.collect()

            # Check that it returns a FactsCollection object
            from rhsmlib.facts.collection import FactsCollection
            self.assertIsInstance(result, FactsCollection)


if __name__ == '__main__':
    unittest.main()