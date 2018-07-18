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

import sys
import os

# Add modules used for building from subscription-manager
syspurpose_home = os.path.abspath(os.path.join(os.path.dirname(__file__), "../packages/syspurpose/src"))
sys.path.append(syspurpose_home)

from subscription_manager import syspurposelib


class SyspurposeStoreInterfaceTests(unittest.TestCase):

    def setUp(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        mock_syspurpose_file = os.path.join(temp_dir, "mock_syspurpose.json")
        syspurpose_values = {}
        with open(mock_syspurpose_file, 'w') as f:
            json.dump(syspurpose_values, f)
            f.flush()
        syspurposelib.USER_SYSPURPOSE = mock_syspurpose_file

    def tearDown(self):
        syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

    def test_save_sla_to_syspurpose_metadata_sla_is_set_when_syspurpose_module_exists(self):
        """
        Tests that the syspurpose sla is set through the syspurposestore interface
        when the syspurpose module is available for import.
        """
        syspurposelib.save_sla_to_syspurpose_metadata("Freemium")

        contents = syspurposelib.SyspurposeStore.read(syspurposelib.USER_SYSPURPOSE).contents
        self.assertEqual(contents.get("service_level_agreement"), "Freemium")

    def test_save_sla_to_syspurpose_metadata_sla_is_not_set_when_None_is_provided(self):
        """
        Tests that the syspurpose sla is not set through the syspurposestore interface
        when None is passed to save_sla_to_syspurpose_metadata method.
        """
        syspurposelib.save_sla_to_syspurpose_metadata(None)

        contents = syspurposelib.SyspurposeStore.read(syspurposelib.USER_SYSPURPOSE).contents
        self.assertEqual(contents.get("service_level_agreement"), None)

    def test_save_sla_to_syspurpose_metadata_sla_is_not_set_when_empty_string_is_provided(self):
        """
        Tests that the syspurpose sla is not set through the syspurposestore interface
        when an empty string is passed to save_sla_to_syspurpose_metadata method.
        """
        syspurposelib.save_sla_to_syspurpose_metadata("")

        contents = syspurposelib.SyspurposeStore.read(syspurposelib.USER_SYSPURPOSE).contents
        self.assertEqual(contents.get("service_level_agreement"), None)

    def test_save_sla_to_syspurpose_metadata_sla_is_not_set_when_syspurpose_module_does_not_exist(self):
        """
        Tests that the syspurpose sla is NOT set through the syspurposestore interface
        when the syspurpose module is not available for import.
        """
        # Remove SyspurposeStore and USER_SYSPURPOSE from syspurposestore_interface's scope temporarily
        # to simulate that importing them failed.
        tmp_syspurpose_store = syspurposelib.SyspurposeStore
        tmp_user_syspurpose = syspurposelib.USER_SYSPURPOSE
        del syspurposelib.SyspurposeStore
        del syspurposelib.USER_SYSPURPOSE

        syspurposelib.save_sla_to_syspurpose_metadata("Freemium")

        # Add SyspurposeStore and USER_SYSPURPOSE back to syspurposestore_interface's scope
        syspurposelib.SyspurposeStore = tmp_syspurpose_store
        syspurposelib.USER_SYSPURPOSE = tmp_user_syspurpose

        # Check that the contents of the syspurpose.json are empty (thus sla was not set)
        contents = syspurposelib.SyspurposeStore.read(syspurposelib.USER_SYSPURPOSE).contents
        self.assertFalse(contents)
