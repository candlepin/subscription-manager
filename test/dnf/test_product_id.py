# Copyright (c) 2022 Red Hat, Inc.
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

import pytest
import unittest
import os
import tempfile
from typing import Union
import types

try:
    import dnf
    import librepo
except ImportError as e:
    pytest.skip(f"DNF dependency could not be imported: {e}", allow_module_level=True)

from plugins.dnf.product_id import DnfProductManager


class TestDnfPluginProductId(unittest.TestCase):
    """
    Test case for DNF plugin product_id (installed as product-id plugin)
    """

    CACHE_FILE = "productid_repo_mapping.json"

    def setUp(self) -> None:
        self.temp_directory: Union[None, tempfile.TemporaryDirectory] = None

    def tearDown(self) -> None:
        if self.temp_directory is not None:
            self.temp_directory.cleanup()

    def test_dummy(self):
        """
        Dummy test of dnf and librepo modules
        """
        self.assertTrue(isinstance(dnf, types.ModuleType))
        self.assertTrue(isinstance(librepo, types.ModuleType))

    def _create_cache_file(self) -> str:
        """
        Create temporary directory and return path of cache file
        """
        self.temp_directory = tempfile.TemporaryDirectory()
        return os.path.join(self.temp_directory.name, self.CACHE_FILE)

    def _create_cache_file_read_only(self) -> str:
        """
        Create read-only temporary directory and return path of cache file
        """
        self.temp_directory = tempfile.TemporaryDirectory()
        # Make directory read only
        os.chmod(self.temp_directory.name, 0x400)
        return os.path.join(self.temp_directory.name, self.CACHE_FILE)

    def test_create_cache_file(self):
        """
        Test that it is possible to create cache file
        """
        cache_file = self._create_cache_file()
        DnfProductManager._write_cache_file({"foo": "bar"}, cache_file)
        data = DnfProductManager._read_cache_file(cache_file)
        self.assertEqual(data, {"foo": "bar"})

    @unittest.skipIf(os.getuid() == 0, "Test cannot be run under root.")
    def test_create_cache_file_in_read_only_directory(self):
        """
        Test that no exception is raised, when dnf plugin tries to create cache file
        in directory that is read-only
        """
        cache_file = self._create_cache_file_read_only()
        DnfProductManager._write_cache_file({"foo": "bar"}, cache_file)

    @unittest.skipIf(os.getuid() == 0, "Test cannot be run under root.")
    def test_read_cache_perm(self):
        """
        Test that no exception is raised, when dnf plugin tries to read cache file
        that process cannot read due to restricted permissions
        """
        cache_file = self._create_cache_file()
        DnfProductManager._write_cache_file({"foo": "bar"}, cache_file)
        os.chmod(cache_file, 0x000)
        data = DnfProductManager._read_cache_file(cache_file)
        self.assertIsNone(data)

    def test_read_non_existing_cache(self):
        """
        Test that no exception is raised, when dnf plugin tries to read non-existing cache file
        """
        data = DnfProductManager._read_cache_file("/path/to/non/existing/file/dot/json")
        self.assertIsNone(data)
