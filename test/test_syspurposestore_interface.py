# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2018 Red Hat, Inc.
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

import json
import shutil
import tempfile
import unittest
from .fixture import set_up_mock_sp_store

import os
import mock


class SyspurposeStoreInterfaceTests(unittest.TestCase):

    def setUp(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        mock_syspurpose_file = os.path.join(temp_dir, "mock_syspurpose.json")
        syspurpose_values = {}
        with open(mock_syspurpose_file, 'w') as f:
            json.dump(syspurpose_values, f)
            f.flush()

        from subscription_manager import syspurposelib

        self.syspurposelib = syspurposelib
        syspurposelib.USER_SYSPURPOSE = mock_syspurpose_file

        syspurpose_patch = mock.patch('subscription_manager.syspurposelib.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

    def _set_up_mock_sp_store(self):
        """
        Sets up the mock syspurpose store with methods that are mock versions of the real deal.
        Allows us to test in the absence of the syspurpose module.
        :return:
        """
        contents = {}
        self.mock_sp_store_contents = contents

        def set(item, value):
            contents[item] = value

        def read(path, raise_on_error=False):
            return self.mock_sp_store

        def unset(item):
            contents[item] = None

        def add(item, value):
            current = contents.get(item, [])
            if value not in current:
                current.append(value)
            contents[item] = current

        def remove(item, value):
            current = contents.get(item)
            if current is not None and isinstance(current, list) and value in current:
                current.remove(value)

        self.mock_sp_store.set = mock.Mock(side_effect=set)
        self.mock_sp_store.read = mock.Mock(side_effect=read)
        self.mock_sp_store.unset = mock.Mock(side_effect=unset)
        self.mock_sp_store.add = mock.Mock(side_effect=add)
        self.mock_sp_store.remove = mock.Mock(side_effect=remove)
        self.mock_sp_store.contents = self.mock_sp_store_contents

    def tearDown(self):
        self.syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

    def test_save_sla_to_syspurpose_metadata_sla_is_set_when_syspurpose_module_exists(self):
        """
        Tests that the syspurpose sla is set through the syspurposestore interface
        when the syspurpose module is available for import.
        """
        self.syspurposelib.save_sla_to_syspurpose_metadata("Freemium")

        contents = self.syspurposelib.read_syspurpose()
        self.assertEqual(contents.get("service_level_agreement"), "Freemium")

    def test_save_sla_to_syspurpose_metadata_sla_is_not_set_when_None_is_provided(self):
        """
        Tests that the syspurpose sla is not set through the syspurposestore interface
        when None is passed to save_sla_to_syspurpose_metadata method.
        """
        self.syspurposelib.save_sla_to_syspurpose_metadata(None)

        contents = self.syspurposelib.read_syspurpose()
        self.assertEqual(contents.get("service_level_agreement"), None)

    def test_save_sla_to_syspurpose_metadata_sla_is_not_set_when_empty_string_is_provided(self):
        """
        Tests that the syspurpose sla is not set through the syspurposestore interface
        when an empty string is passed to save_sla_to_syspurpose_metadata method.
        """
        self.syspurposelib.save_sla_to_syspurpose_metadata("")

        contents = self.syspurposelib.read_syspurpose()
        self.assertEqual(contents.get("service_level_agreement"), None)

    def test_save_sla_to_syspurpose_metadata_sla_is_not_set_when_syspurpose_module_does_not_exist(self):
        """
        Tests that the syspurpose sla is NOT set through the syspurposestore interface
        when the syspurpose module is not available for import.
        """
        # Remove SyspurposeStore and USER_SYSPURPOSE from syspurposestore_interface's scope temporarily
        # to simulate that importing them failed.
        tmp_syspurpose_store = self.syspurposelib.SyncedStore
        tmp_user_syspurpose = self.syspurposelib.USER_SYSPURPOSE
        del self.syspurposelib.SyncedStore
        del self.syspurposelib.USER_SYSPURPOSE

        self.syspurposelib.save_sla_to_syspurpose_metadata("Freemium")

        # Add SyspurposeStore and USER_SYSPURPOSE back to syspurposestore_interface's scope
        self.syspurposelib.SyncedStore = tmp_syspurpose_store
        self.syspurposelib.USER_SYSPURPOSE = tmp_user_syspurpose

        # Check that the contents of the syspurpose.json are empty (thus sla was not set)
        contents = self.syspurposelib.read_syspurpose()
        self.assertFalse(contents)
