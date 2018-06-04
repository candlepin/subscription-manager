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
import os
import shutil
import tempfile
import unittest

from subscription_manager import intentstore_interface


class IntentStoreInterfaceTests(unittest.TestCase):

    def setUp(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        mock_intent_file = os.path.join(temp_dir, "mock_intent.json")
        intent_values = {}
        with open(mock_intent_file, 'w') as f:
            json.dump(intent_values, f)
            f.flush()
        intentstore_interface.USER_INTENT = mock_intent_file

    def tearDown(self):
        intentstore_interface.USER_INTENT = "/etc/rhsm/intent/intent.json"

    def test_save_sla_to_intent_metadata_sla_is_set_when_intentctl_module_exists(self):
        """
        Tests that the intent sla is set through the intentstore interface
        when the intentctl module is available for import.
        """
        intentstore_interface.save_sla_to_intent_metadata("Freemium")

        contents = intentstore_interface.IntentStore.read(intentstore_interface.USER_INTENT).contents
        self.assertEqual(contents.get("service_level_agreement"), "Freemium")

    def test_save_sla_to_intent_metadata_sla_is_not_set_when_None_is_provided(self):
        """
        Tests that the intent sla is not set through the intentstore interface
        when None is passed to save_sla_to_intent_metadata method.
        """
        intentstore_interface.save_sla_to_intent_metadata(None)

        contents = intentstore_interface.IntentStore.read(intentstore_interface.USER_INTENT).contents
        self.assertEqual(contents.get("service_level_agreement"), None)

    def test_save_sla_to_intent_metadata_sla_is_not_set_when_empty_string_is_provided(self):
        """
        Tests that the intent sla is not set through the intentstore interface
        when an empty string is passed to save_sla_to_intent_metadata method.
        """
        intentstore_interface.save_sla_to_intent_metadata("")

        contents = intentstore_interface.IntentStore.read(intentstore_interface.USER_INTENT).contents
        self.assertEqual(contents.get("service_level_agreement"), None)

    def test_save_sla_to_intent_metadata_sla_is_not_set_when_intentctl_module_does_not_exist(self):
        """
        Tests that the intent sla is NOT set through the intentstore interface
        when the intentctl module is not available for import.
        """
        # Remove IntentStore and USER_INTENT from intentstore_interface's scope temporarily
        # to simulate that importing them failed.
        tmp_intent_store = intentstore_interface.IntentStore
        tmp_user_intent = intentstore_interface.USER_INTENT
        del intentstore_interface.IntentStore
        del intentstore_interface.USER_INTENT

        intentstore_interface.save_sla_to_intent_metadata("Freemium")

        # Add IntentStore and USER_INTENT back to intentstore_interface's scope
        intentstore_interface.IntentStore = tmp_intent_store
        intentstore_interface.USER_INTENT = tmp_user_intent

        # Check that the contents of the intent.json are empty (thus sla was not set)
        contents = intentstore_interface.IntentStore.read(intentstore_interface.USER_INTENT).contents
        self.assertFalse(contents)
