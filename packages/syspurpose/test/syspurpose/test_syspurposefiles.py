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

from base import SyspurposeTestBase
import json
import os

from syspurpose import files


class SyspurposeStoreTests(SyspurposeTestBase):

    def test_new_syspurpose_store(self):
        """
        A smoke test to ensure nothing bizarre happens on SyspurposeStore object creation
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        self.assertEqual(syspurpose_store.contents, {})
        self.assertEqual(syspurpose_store.path, temp_dir)

    def test_read_file_non_existent_file(self):
        """
        Can the SyspurposeStore.read_file method handle attempting to read a file which does not exist?
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        self.assertFalse(os.path.exists(temp_dir))

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        res = self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertFalse(bool(res))

    def test_read_file_existent_file(self):
        """
        The SyspurposeStore.read_file method should return True if the file was successfully read.
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {}
        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        self.assertTrue(os.path.exists(temp_dir))

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        res = self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertTrue(bool(res))

    def _read_file(self, file_contents=None, expected_contents=None):
        """
        Utility method for logic common to the *read_file* tests.
        :param file_contents:
        :param expected_contents:
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        with open(temp_dir, 'w') as f:
            if file_contents and not isinstance(file_contents, str):
                json.dump(file_contents, f)
            else:
                f.write(file_contents or '')
            f.flush()
        self.assertTrue(os.path.exists(temp_dir), "Unable to create test file in temp dir")

        # Actually do the test
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertEqual(syspurpose_store.contents, expected_contents)

    def test_read_file_empty_file(self):
        """
        Can the SyspurposeStore.read_file method handle attempting to read an empty file?
        :return:
        """
        self._read_file(file_contents='', expected_contents={})

    def test_read_file_non_empty(self):
        """
        Lets see if we can read a file that is non-empty
        :return:
        """
        test_data = {"arbitrary": "data"}
        self._read_file(file_contents=test_data, expected_contents=test_data)

    def test_create(self):
        """
        Verify that the create method will create the directory (if needed), and that the resulting \
        file in the directory is writable by us.
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        self.assertRaisesNothing(syspurpose_store.create)
        # We should have a new file in the temp_dir that we can access for writing
        self.assertTrue(os.path.exists(temp_dir))
        self.assertTrue(os.access(temp_dir, os.W_OK))

    def test_add(self):
        """
        Verify that the add method of SyspurposeStore is able to add items to lists of items
        in the store, whether they existed prior or not.
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}
        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Brand new unseen key is added
        res = self.assertRaisesNothing(syspurpose_store.add, "new_key", "new_value")
        self.assertIn("new_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["new_key"], ["new_value"])
        self.assertTrue(res, "The add method should return true when the store has changed")

        # Add to an already seen existing key
        res = self.assertRaisesNothing(syspurpose_store.add, "already_present_key", "new_value_2")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["already_present_key"], ["preexisting_value", "new_value_2"])
        self.assertTrue(res, "The add method should return true when the store has changed")

    def test_remove(self):
        """
        Verify that the remove method can remove items from the store.
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}
        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Remove an item from the store which we have previously seen
        res = self.assertRaisesNothing(syspurpose_store.remove, "already_present_key", "preexisting_value")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["already_present_key"], [])
        self.assertTrue(res, "The remove method should return true when the store has changed")

        # Try to remove an item that we've previously not seen
        res = self.assertRaisesNothing(syspurpose_store.remove, "new_key", "any_value")
        self.assertFalse(res, "The remove method should return false when the store has not changed")

    def test_unset(self):
        """
        Verify the operation of the unset method of SyspurposeStore
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        res = self.assertRaisesNothing(syspurpose_store.unset, "already_present_key")
        # We expect a value of true from this method when the store was changed
        self.assertTrue(res, "The unset method should return true when the store has changed")
        self.assertIn("already_present_key", syspurpose_store.contents, msg="Expected the key to still be in the contents, but reset to None")
        # We expect the item to have been unset to None
        self.assertEqual(syspurpose_store.contents["already_present_key"], None)

        res = self.assertRaisesNothing(syspurpose_store.unset, "unseen_key")
        # We expect falsey values when the store was not modified
        self.assertFalse(res, "The unset method should return false when the store has not changed")
        self.assertNotIn("unseen_key", syspurpose_store.contents, msg="The key passed to unset, has been added to the store")

    def test_set(self):
        """
        Verify the operation of the set method of SyspurposeStore
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": "old_value"}

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Check the behaviour of manipulating an existing key with an identical value (no update)
        res = self.assertRaisesNothing(syspurpose_store.set, "already_present_key", "old_value")
        self.assertFalse(res, "When a value is not actually changed, set should return false")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["already_present_key"], "old_value")

        # Modify existing item
        res = self.assertRaisesNothing(syspurpose_store.set, "already_present_key", "new_value")
        self.assertTrue(res, "When an item is set to a new value, set should return true")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["already_present_key"], "new_value")

        # Add new item set to a new value
        res = self.assertRaisesNothing(syspurpose_store.set, "new_key", "new_value_2")
        self.assertTrue(res, "When an item is set to a new value, set should return true")
        self.assertIn("new_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["new_key"], "new_value_2")

    def test_write(self):
        """
        Verify that the SyspurposeStore can write changes to the expected file.
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"arbitrary_key": "arbitrary_value"}
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        self.assertRaisesNothing(syspurpose_store.write)

        with open(temp_dir, 'r') as f:
            actual_contents = self.assertRaisesNothing(json.load, f)

        self.assertDictEqual(actual_contents, test_data)

    def test_read(self):
        """
        Does read properly initialize a new SyspurposeStore?
        :return:
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"arbitrary_key": "arbitrary_value"}

        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore.read, temp_dir)
        self.assertDictEqual(syspurpose_store.contents, test_data)
