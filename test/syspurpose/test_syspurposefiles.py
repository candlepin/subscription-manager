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

from .base import SyspurposeTestBase, write_to_file_utf8, Capture
import io
import json
import os
import mock

from syspurpose import files, utils
from syspurpose.files import detect_changed, three_way_merge, UNSUPPORTED, SyncedStore, SyncResult


class SyspurposeStoreTests(SyspurposeTestBase):

    def test_new_syspurpose_store(self):
        """
        A smoke test to ensure nothing bizarre happens on SyspurposeStore object creation
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        self.assertEqual(syspurpose_store.contents, {})
        self.assertEqual(syspurpose_store.path, temp_dir)

    def test_read_file_non_existent_file(self):
        """
        Can the SyspurposeStore.read_file method handle attempting to read a file which does not exist?
        """
        temp_file = os.path.join(self._mktmp(), 'syspurpose_file.json')
        self.assertFalse(os.path.exists(temp_file))

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_file)
        res = self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertFalse(bool(res))

    def test_read_file_existent_file(self):
        """
        The SyspurposeStore.read_file method should return True if the file was successfully read.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        self.assertTrue(os.path.exists(temp_dir))

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        res = self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertTrue(bool(res))

    def test_read_file_with_unicode_content(self):
        """
        The SyspurposeStore.read_file method should return True if the file with unicode content was successfully read.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {'key1': u'Νίκος', 'key2': [u'value_with_ř']}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        self.assertTrue(os.path.exists(temp_dir))

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        res = self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertTrue(bool(res))

    def _read_file(self, file_contents=None, expected_contents=None):
        """
        Utility method for logic common to the *read_file* tests.
        :param file_contents:
        :param expected_contents:
        :return: None
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            if file_contents and not isinstance(file_contents, str):
                utils.write_to_file_utf8(f, file_contents)
            else:
                f.write(utils.make_utf8(file_contents or ''))
            f.flush()
        self.assertTrue(os.path.exists(temp_dir), "Unable to create test file in temp dir")

        # Actually do the test
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        self.assertRaisesNothing(syspurpose_store.read_file)
        self.assertEqual(syspurpose_store.contents, expected_contents)

    def test_read_file_empty_file(self):
        """
        Can the SyspurposeStore.read_file method handle attempting to read an empty file?
        """
        self._read_file(file_contents='', expected_contents={})

    def test_read_file_non_empty(self):
        """
        Lets see if we can read a file that is non-empty
        """
        test_data = {"arbitrary": "data"}
        self._read_file(file_contents=test_data, expected_contents=test_data)

    def test_create(self):
        """
        Verify that the create method will create the directory (if needed), and that the resulting \
        file in the directory is writable by us.
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
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

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

    def test_add_new_value_to_key_with_null_value(self):
        """
        Verify that the add method of SyspurposeStore is able to add item to key with
        null value
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": None}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Brand new unseen key is added
        res = self.assertRaisesNothing(syspurpose_store.add, "already_present_key", "new_value")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["already_present_key"], ["new_value"])
        self.assertTrue(res, "The add method should return true when the store has changed")

    def test_add_does_not_override_existing_scalar_value(self):
        """
        Verify that the add method of SyspurposeStore is able to add items to a property
        in the store, without overriding an existing scalar value the property might already contain.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": "preexisting_scalar_value"}
        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Add to an already seen existing key, that contains a scalar value
        res = self.assertRaisesNothing(syspurpose_store.add, "already_present_key", "new_value_2")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents["already_present_key"], ["preexisting_scalar_value", "new_value_2"])
        self.assertTrue(res, "The add method should return true when the store has changed")

    def test_add_with_unicode_strings(self):
        """
        Verify that the add method of SyspurposeStore is able to add unicode strings to lists of items
        in the store.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {u'ονόματα': [u'Νίκος']}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Add to an already seen existing key
        res = self.assertRaisesNothing(syspurpose_store.add, 'ονόματα', 'Κώστας')
        self.assertIn(u'ονόματα', syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents[u'ονόματα'], [u'Νίκος', u'Κώστας'])
        self.assertTrue(res, "The add method should return true when the store has changed")

    def test_add_does_not_duplicate_existing_value(self):
        """
        Verify that the add method of SyspurposeStore will not add an item to a list, if that list already contains
        the item we're trying to add.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}
        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Try to add a value that already exists to an already seen existing key
        self.assertRaisesNothing(syspurpose_store.add, "already_present_key", "preexisting_value")
        self.assertIn("already_present_key", syspurpose_store.contents)
        self.assertEqual(len(syspurpose_store.contents["already_present_key"]), 1)
        self.assertEqual(syspurpose_store.contents["already_present_key"], ["preexisting_value"])

    def test_remove(self):
        """
        Verify that the remove method can remove items from the store.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

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

    def test_remove_unsets_existing_scalar_value(self):
        """
        Verify that the remove_command, in case the value specified for removal is a scalar/non-list value,
        unsets this value.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": "preexisting_scalar_value"}
        with open(temp_dir, 'w') as f:
            json.dump(test_data, f)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Remove an item from the store which we have previously seen, whose value is scalar / not contained in a list
        res = self.assertRaisesNothing(syspurpose_store.remove, "already_present_key", "preexisting_scalar_value")
        self.assertNotIn("already_present_key", syspurpose_store.contents)
        self.assertTrue(res, "The remove method should return true when the store has changed")

    def test_remove_with_unicode_strings(self):
        """
        Verify that the remove method of SyspurposeStore is able to remove unicode strings from lists of items
        in the store.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {u'ονόματα': [u'Νίκος', u'Κώστας']}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Remove from an already seen existing key
        res = self.assertRaisesNothing(syspurpose_store.remove, 'ονόματα', 'Κώστας')
        self.assertIn(u'ονόματα', syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents[u'ονόματα'], [u'Νίκος'])
        self.assertTrue(res, "The add method should return true when the store has changed")

    def test_unset(self):
        """
        Verify the operation of the unset method of SyspurposeStore
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"already_present_key": ["preexisting_value"]}

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        res = self.assertRaisesNothing(syspurpose_store.unset, "already_present_key")
        # We expect a value of true from this method when the store was changed
        self.assertTrue(res, "The unset method should return true when the store has changed")
        self.assertNotIn("already_present_key", syspurpose_store.contents, msg="Expected the key to no longer be present")

        res = self.assertRaisesNothing(syspurpose_store.unset, "unseen_key")
        # We expect falsey values when the store was not modified
        self.assertFalse(res, "The unset method should return false when the store has not changed")
        self.assertNotIn("unseen_key", syspurpose_store.contents, msg="The key passed to unset, has been added to the store")

    def test_unset_with_unicode_strings(self):
        """
        Verify that the unset method of SyspurposeStore is able to unset unicode strings from items
        in the store.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {u'ονόματα': [u'Νίκος']}
        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        res = self.assertRaisesNothing(syspurpose_store.unset, "ονόματα")
        # We expect a value of true from this method when the store was changed
        self.assertTrue(res, "The unset method should return true when the store has changed")
        self.assertNotIn(u'ονόματα', syspurpose_store.contents, msg="Expected the key to no longer be present")

        res = self.assertRaisesNothing(syspurpose_store.unset, 'άκυρο_κλειδί')
        # We expect falsey values when the store was not modified
        self.assertFalse(res, "The unset method should return false when the store has not changed")
        self.assertNotIn(u'άκυρο_κλειδί', syspurpose_store.contents, msg="The key passed to unset, has been added to the store")

    def test_unset_sla(self):
        """
        Verify the unset operation handles the special case for the SLA field
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"service_level_agreement": "preexisting_value"}

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        res = self.assertRaisesNothing(syspurpose_store.unset, "service_level_agreement")
        # We expect a value of true from this method when the store was changed
        self.assertTrue(res, "The unset method should return true when the store has changed")
        self.assertIn("service_level_agreement", syspurpose_store.contents, msg="Expected the key to still be in the contents, but reset to an empty string")
        # We expect the item to have been unset to None
        self.assertEqual(syspurpose_store.contents["service_level_agreement"], '')

    def test_set(self):
        """
        Verify the operation of the set method of SyspurposeStore
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

    def test_set_with_unicode_strings(self):
        """
        Verify the operation of the set method of SyspurposeStore when using unicode strings
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {u'ονόματα': u'Νίκος'}

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        # Check the behaviour of manipulating an existing key with an identical value (no update)
        res = self.assertRaisesNothing(syspurpose_store.set, 'ονόματα', 'Νίκος')
        self.assertFalse(res, "When a value is not actually changed, set should return false")
        self.assertIn(u'ονόματα', syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents[u'ονόματα'], u'Νίκος')

        # Modify existing item
        res = self.assertRaisesNothing(syspurpose_store.set, 'ονόματα', 'Κώστας')
        self.assertTrue(res, "When an item is set to a new value, set should return true")
        self.assertIn(u'ονόματα', syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents[u'ονόματα'], u'Κώστας')

        # Add new item set to a new value
        res = self.assertRaisesNothing(syspurpose_store.set, 'καινούργιο', 'Άλεξανδρος')
        self.assertTrue(res, "When an item is set to a new value, set should return true")
        self.assertIn(u'καινούργιο', syspurpose_store.contents)
        self.assertEqual(syspurpose_store.contents[u'καινούργιο'], u'Άλεξανδρος')

    def test_write(self):
        """
        Verify that the SyspurposeStore can write changes to the expected file.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"arbitrary_key": "arbitrary_value"}
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        self.assertRaisesNothing(syspurpose_store.write)

        with io.open(temp_dir, 'r', encoding='utf-8') as f:
            actual_contents = self.assertRaisesNothing(json.load, f)

        self.assertDictEqual(actual_contents, test_data)

    def test_write_with_unicode_content(self):
        """
        Verify that the SyspurposeStore can write changes that include unicode strings to the expected file.
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {u'όνομα': u'Νίκος'}
        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore, temp_dir)
        syspurpose_store.contents = dict(**test_data)

        self.assertRaisesNothing(syspurpose_store.write)

        with io.open(temp_dir, 'r', encoding='utf-8') as f:
            actual_contents = self.assertRaisesNothing(json.load, f)

        self.assertDictEqual(actual_contents, test_data)

    def test_read(self):
        """
        Does read properly initialize a new SyspurposeStore?
        """
        temp_dir = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {"arbitrary_key": "arbitrary_value"}

        with io.open(temp_dir, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = self.assertRaisesNothing(files.SyspurposeStore.read, temp_dir)
        self.assertDictEqual(syspurpose_store.contents, test_data)


class TestSyncedStore(SyspurposeTestBase):
    """
    Tests to show the proper overall syncing functionality of the SyncedStore class.
    This class (at the time of writing) is responsible for maintaining the local syspurpose file,
    the local syspurpose cache file and retriving and syncing the syspurpose values from the server
    should the system be able to.
    """

    # These are the values we typically expect the server will return when no syspurpose is set.
    default_remote_values = {
        "role": None,
        "usage": None,
        "addOns": [],
        "serviceLevel": u""
    }

    def setUp(self):
        self.temp_dir = self._mktmp()
        self.temp_cache_dir = self._mktmp()
        # For these tests we want to make sure that the paths that are used are our mock files

        user_syspurpose_dir_patch = mock.patch('syspurpose.files.USER_SYSPURPOSE_DIR', self.temp_dir)
        user_syspurpose_dir_patch.start()
        self.addCleanup(user_syspurpose_dir_patch.stop)

        cache_dir_patch = mock.patch('syspurpose.files.CACHE_DIR', self.temp_cache_dir)
        cache_dir_patch.start()
        self.addCleanup(cache_dir_patch.stop)

        self.local_syspurpose_file = os.path.join(self.temp_dir, 'syspurpose.json')
        self.cache_syspurpose_file = os.path.join(self.temp_cache_dir, 'cache.json')

        # For these tests we want to make sure that the paths that are used are our mock files
        synced_store_local_patch = mock.patch('syspurpose.files.SyncedStore.PATH',
                                              self.local_syspurpose_file)
        synced_store_local_patch.start()
        self.addCleanup(synced_store_local_patch.stop)

        synced_store_cache_patch = mock.patch('syspurpose.files.SyncedStore.CACHE_PATH',
                                              self.cache_syspurpose_file)
        synced_store_cache_patch.start()
        self.addCleanup(synced_store_cache_patch.stop)

        self.uep = mock.Mock()
        self.uep.getConsumer.return_value = self.default_remote_values

        # Fake that the connected server supports syspurpose
        self.uep.has_capability = mock.Mock(side_effect=lambda x: x in ['syspurpose'])

        self.uep.getOwner.return_value = {
            "created": "2020-06-22T13:57:27+0000",
            "updated": "2020-06-22T13:57:27+0000",
            "id": "ff80808172dc51a10172dc51cb3e0004",
            "key": "admin",
            "displayName": "Admin Owner",
            "parentOwner": None,
            "contentPrefix": None,
            "defaultServiceLevel": None,
            "upstreamConsumer": None,
            "logLevel": None,
            "autobindDisabled": None,
            "autobindHypervisorDisabled": None,
            "contentAccessMode": "entitlement",
            "contentAccessModeList": "entitlement",
            "lastRefreshed": None,
            "href": "/owners/admin"
        }

        self.uep.getOwnerSyspurposeValidFields.return_value = {
            "owner": {
                "id": "ff80808172dc51a10172dc51cb3e0004",
                "key": "admin",
                "displayName": "Admin Owner",
                "href": "/owners/admin"
            },
            "systemPurposeAttributes": {
                "addons": [
                    "ADDON1",
                    "ADDON3",
                    "ADDON2"
                ],
                "usage": [
                    "Production",
                    "Development"
                ],
                "roles": [
                    "SP Starter",
                    "SP Server"
                ],
                "support_level": [
                    "Full-Service",
                    "Super",
                    "Layered",
                    "Standard",
                    "Premium",
                    "None"
                ]
            }
        }

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_enter_exit_methods_set(self, mock_sync):
        """
        Test that synced store is automatically synced, when set method is used
        in block of with statement
        """
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.set('foo', 'bar')
        mock_sync.assert_called_once()

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_enter_exit_methods_not_used(self, mock_sync):
        """
        Test that synced store is not automatically synced, when set method is
        not used in the block of with statement
        """
        with SyncedStore(self.uep, consumer_uuid="something"):
            pass
        mock_sync.assert_not_called()

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_enter_exit_methods_unset(self, mock_sync):
        """
        Test that synced store is automatically synced, when unset method is used
        in block of with statement
        """
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'foo': 'bar'})
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            self.assertFalse(synced_store.changed)
            synced_store.unset('foo')
            self.assertTrue(synced_store.changed)
        mock_sync.assert_called_once()

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_enter_exit_methods_add(self, mock_sync):
        """
        Test that synced store is automatically synced, when add method is used
        in block of with statement
        """
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            self.assertFalse(synced_store.changed)
            synced_store.add('foo', 'bar')
            synced_store.add('foo', 'boo')
            self.assertTrue(synced_store.changed)
        mock_sync.assert_called_once()

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_add_method_existing_value_not_list(self, mock_sync):
        """
        Test add method for the case, when existing value is not list, but
        it is simple value. Final value should be list.
        """

        # First set value using set() method
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.set('foo', 'bar')
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        self.assertTrue('foo' in local_result)
        self.assertEqual(local_result['foo'], 'bar')

        # Then try to extend this attribute using add() method. Final value should be
        # list not single value
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.add('foo', 'boo')
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        self.assertTrue('foo' in local_result)
        self.assertEqual(local_result['foo'], ['bar', 'boo'])

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_add_method_none_value(self, mock_sync):
        """
        Test add method for the case, when existing value is not list, but
        it is None value. Final value should be list.
        """

        # First set value using set() method
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.set('foo', None)
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        self.assertTrue('foo' in local_result)
        self.assertEqual(local_result['foo'], None)

        # Then try to extend this attribute using add() method. Final value should be
        # list not single value
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.add('foo', 'boo')
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        self.assertTrue('foo' in local_result)
        self.assertEqual(local_result['foo'], ['boo'])

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_enter_exit_methods_remove(self, mock_sync):
        """
        Test that synced store is automatically synced, when remove method is used
        in block of with statement
        """
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'foo': ['bar'], 'cool': 'shark'})
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            self.assertFalse(synced_store.changed)
            synced_store.remove('foo', 'bar')
            self.assertTrue(synced_store.changed)
        mock_sync.assert_called_once()
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        print(local_result)
        self.assertTrue('cool' in local_result)
        self.assertEqual(local_result['cool'], 'shark')
        self.assertTrue('foo' in local_result)
        self.assertEqual(local_result['foo'], [])

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_enter_exit_methods_remove_one_value(self, mock_sync):
        """
        Test that synced store is automatically synced, when remove method is used
        in block of with statement. Test the case, when value is not list.
        """
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'foo': 'bar'})
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            self.assertFalse(synced_store.changed)
            synced_store.remove('foo', 'bar')
            self.assertTrue(synced_store.changed)
        mock_sync.assert_called_once()

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_remove_non_existent_value(self, mock_sync):
        """
        Test that removing non-existent value will not mark synced store as changed
        """
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'foo': ['bar']})
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            self.assertFalse(synced_store.changed)
            synced_store.remove('foo', 'boooo')
            self.assertFalse(synced_store.changed)
        mock_sync.assert_not_called()

    @mock.patch('syspurpose.files.SyncedStore.sync')
    def test_remove_non_existent_key(self, mock_sync):
        """
        Test that removing non-existent key will not mark synced store as changed
        """
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'foo': ['bar']})
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            self.assertFalse(synced_store.changed)
            synced_store.remove('non-existent', 'foo_bar')
            self.assertFalse(synced_store.changed)
        mock_sync.assert_not_called()

    @mock.patch('syspurpose.files.SyncedStore._sync_local_only')
    def test_sync_localy_when_server_is_not_responding(self, mock_sync_local_only):
        """
        Test that only local syncing is triggered, when we are not able to detect
        if candlepin server has syspurpose capability
        """
        def has_capability(*args, **kwargs):
            raise TypeError('Exception for testing')
        self.uep.has_capability = mock.Mock(side_effect=has_capability)
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.set('foo', 'bar')
        mock_sync_local_only.assert_called_once()

    @mock.patch('syspurpose.files.SyncedStore._sync_local_only')
    def test_sync_local_only(self, mock_sync_local_only):
        """
        Test that only local syncing is triggered, when server is down or
        the system is not registered
        """
        self.uep.has_capability = mock.Mock(side_effect=lambda x: False)
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.set('foo', 'bar')
        mock_sync_local_only.assert_called_once()

    def test_sync_local_only_extend_existing_values(self):
        """
        Test that local syncing does not overwrite existing values
        """
        self.uep.has_capability = mock.Mock(side_effect=lambda x: False)
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'foo': 'bar'})
        with SyncedStore(self.uep, consumer_uuid="something") as synced_store:
            synced_store.set('cool', 'dear')
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        self.assertTrue('foo' in local_result)
        self.assertEqual(local_result['foo'], 'bar')
        self.assertTrue('cool' in local_result)
        self.assertEqual(local_result['cool'], 'dear')

    def test_falsey_values_removed_from_local_empty_local(self):
        # The falsey values ([], "", {}, None) should never end up after a SyncedStore.sync in
        # the local syspurpose file.
        self._assert_falsey_values_removed_from_local(remote_contents=self.default_remote_values,
                                                      local_contents={},
                                                      cache_contents={})

    def test_falsey_values_removed_from_local_with_local_values(self):
        # The falsey values ([], "", {}, None) should never end up after a SyncedStore.sync in
        # the local syspurpose file. Even if they were added to the local file itself
        self._assert_falsey_values_removed_from_local(remote_contents=self.default_remote_values,
                                                      local_contents={"role": ""},
                                                      cache_contents={})

    def test_falsey_values_removed_from_local_empty_strings_from_remote(self):
        # The falsey values ([], "", {}, None) should never end up after a SyncedStore.sync in
        # the local syspurpose file.

        remote_content = {
            "role": "",
            "usage": "",
            "serviceLevel": "",
            "addOns": []
        }
        self._assert_falsey_values_removed_from_local(remote_contents=remote_content,
                                                      local_contents={},
                                                      cache_contents={})

    def _assert_falsey_values_removed_from_local(self, remote_contents, local_contents, cache_contents):
        self.uep.getConsumer.return_value = remote_contents

        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), local_contents)
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), cache_contents)

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))
        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        # All the values from the local file should be truthy.
        self.assertTrue(all(local_result[key] for key in local_result))

        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))
        # The cache should contain the entire set of values from the SyncResult
        self.assertDictEqual(cache_result, result.result)

    def test_list_items_are_order_agnostic(self):
        addons = [1, 2]
        self.uep.getConsumer.return_value = {'addOns': addons}

        # Write an out of order list to both the local and cache
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {'addons': addons[::-1]})
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), {'addons': addons[::-1]})

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        self.assertSetEqual(set(result.result['addons']), set(local_result['addons']),
                            'Expected local file to have the same set of addons as the result')
        self.assertSetEqual(set(result.result['addons']), set(cache_result['addons']),
                            'Expected cache file to have the same set of addons as the result')

    def test_server_side_falsey_removes_value_locally(self):
        initial_syspurpose = {'role': 'something'}
        remote_contents = {'role': ''}
        self.uep.getConsumer.return_value = remote_contents

        # Write an out of order list to both the local and cache
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), initial_syspurpose)
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), initial_syspurpose)

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        self.assertTrue('role' not in local_result,
                        'The role was falsey and should not have been in the local file')
        self.assertTrue('role' in cache_result and cache_result['role'] == remote_contents['role'],
                        'Expected the cache file to contain the same value for role as the remote')

    def test_values_not_known_server_side_are_left_alone(self):
        cache_contents = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'service_level_agreement': u'',
            u'addons': []
        }
        local_contents = {
            u'role': cache_contents[u'role'],
            u'usage': cache_contents[u'usage'],
            u'made_up_key': u'arbitrary_value'  # this key was added and is not known
        }
        remote_contents = {
            u'role': u'remote_role',
            u'usage': u'',  # Usage has been reset on the server side, should be removed locally
            u'serviceLevel': u'',
            u'addOns': []
        }

        self.uep.getConsumer.return_value = remote_contents

        # Write an out of order list to both the local and cache
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), local_contents)
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), cache_contents)

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        expected_local = {
            u'role': remote_contents['role'],
            u'made_up_key': local_contents['made_up_key']
        }
        expected_cache = {
            u'role': remote_contents['role'],
            u'usage': remote_contents['usage'],
            u'made_up_key': local_contents['made_up_key'],
            u'addons': [],
            u'service_level_agreement': u''
        }

        self.assert_equal_dict(expected_local, local_result)
        self.assert_equal_dict(expected_cache, cache_result)

    def test_same_values_not_synced_with_server(self):
        cache_contents = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'service_level_agreement': u'initial_sla'
        }
        local_contents = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'service_level_agreement': u'initial_sla'
        }
        remote_contents = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'serviceLevel': u'initial_sla'
        }

        self.uep.getConsumer.return_value = remote_contents
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), cache_contents)
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), local_contents)

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        # When values are still the same, then client should not try to sync
        # same values with server
        self.uep.updateConsumer.assert_not_called()

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        expected_local = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'service_level_agreement': u'initial_sla'
        }
        expected_cache = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'service_level_agreement': u'initial_sla',
            u'addons': None
        }

        self.assert_equal_dict(expected_cache, cache_result)
        self.assert_equal_dict(expected_local, local_result)

    def test_server_does_not_support_syspurpose(self):
        # This is how we detect if we have syspurpose support
        self.uep.has_capability = mock.Mock(side_effect=lambda x: x in [])

        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {u'role': u'initial'})
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), {})

        synced_store = SyncedStore(self.uep, consumer_uuid="something")

        remote_content = synced_store.get_remote_contents()
        self.assertEqual(remote_content, {})

        self.assertRaisesNothing(synced_store.set, u'role', u'new_role')
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        # The cache should not be updated at all
        self.assert_equal_dict({}, cache_result)
        self.assert_equal_dict({u'role': u'new_role'}, local_result)

        self.uep.updateConsumer.assert_not_called()

    def test_server_setting_unsupported_value(self):
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {u'role': u''})
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), {})

        synced_store = SyncedStore(self.uep, consumer_uuid="something", use_valid_fields=True)

        with Capture() as captured:
            synced_store.set(u'role', u'new_role')
            self.assertTrue('Warning: Provided value "new_role" is not included in the list of valid values for attribute role' in captured.out)
            self.assertTrue("SP Starter" in captured.out)
            self.assertTrue("SP Server" in captured.out)

    def test_server_setting_unsupported_key(self):
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {u'role': u''})
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), {})

        synced_store = SyncedStore(self.uep, consumer_uuid="something", use_valid_fields=True)

        with Capture() as captured:
            synced_store.set(u'foo', u'bar')
            self.assertTrue('Warning: Provided key "foo" is not included in the list of valid keys' in captured.out)
            self.assertTrue("addons" in captured.out)
            self.assertTrue("usage" in captured.out)
            self.assertTrue("role" in captured.out)
            self.assertTrue("service_level_agreement" in captured.out)

    def test_server_upgraded_to_support_syspurpose(self):
        # This one attempts to show that if a server does not support syspurpose and then does
        # after an upgrade perhaps, that we do the right thing (not unsetting all the user set
        # values

        self.uep.has_capability = mock.Mock(side_effect=lambda x: x in [])
        write_to_file_utf8(io.open(self.local_syspurpose_file, 'w'), {u'role': u'initial'})
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), {})

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        self.assert_equal_dict({u'role': u'initial'}, local_result)
        self.assert_equal_dict({}, cache_result)

        # Now the "fake" upgrade

        self.uep.has_capability = mock.Mock(side_effect=lambda x: x in ["syspurpose"])
        self.uep.getConsumer.return_value = self.default_remote_values

        synced_store = SyncedStore(self.uep, consumer_uuid="something")
        result = self.assertRaisesNothing(synced_store.sync)

        self.assertTrue(isinstance(result, SyncResult))

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        expected_cache = {
            u'role': u'initial',  # This was set locally before and should still be
            u'usage': self.default_remote_values['usage'],
            u'service_level_agreement': self.default_remote_values['serviceLevel'],
            u'addons': self.default_remote_values['addOns']
        }

        self.assert_equal_dict({u'role': u'initial'}, local_result)
        self.assert_equal_dict(expected_cache, cache_result)

    def test_user_deletes_syspurpose_file(self):
        cache_contents = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'service_level_agreement': u'',
            u'addons': []
        }
        remote_contents = {
            u'role': u'initial_role',
            u'usage': u'initial_usage',
            u'serviceLevel': u'',
            u'addOns': []
        }
        consumer_uuid = "something"
        self.uep.getConsumer.return_value = remote_contents
        write_to_file_utf8(io.open(self.cache_syspurpose_file, 'w'), cache_contents)
        # We don't write anything to the self.local_syspurpose_file anywhere else, so not making
        # one is equivalent to removing an existing one.

        synced_store = SyncedStore(self.uep, consumer_uuid=consumer_uuid)
        self.assertRaisesNothing(synced_store.sync)

        expected_cache = {u'service_level_agreement': u'',
                          u'addons': []}
        expected_local = {}

        local_result = json.load(io.open(self.local_syspurpose_file, 'r'))
        cache_result = json.load(io.open(self.cache_syspurpose_file, 'r'))

        self.assert_equal_dict(expected_local, local_result)
        self.assert_equal_dict(expected_cache, cache_result)
        self.uep.updateConsumer.assert_called_once_with(consumer_uuid,
                                                        role=u"",
                                                        usage=u"",
                                                        service_level=u"",
                                                        addons=[])

    def test_read_file_non_existent_directory(self):
        """
        Test the SyspurposeStore.read_file can resurrect from situation, when directory /etc/rhsm/syspurpose
        does not exist
        """
        # Delete the temporary directory
        os.rmdir(self.temp_dir)

        consumer_uuid = "something"
        synced_store = SyncedStore(self.uep, consumer_uuid=consumer_uuid)
        local_content = self.assertRaisesNothing(synced_store.get_local_contents)
        self.assertEqual(local_content, {})

        # Make sure that the directory was created
        res = os.path.isdir(self.temp_dir)
        self.assertTrue(res)

    def test_read_file_non_existent_cache_directory(self):
        """
        Test the SyspurposeStore.read_file can resurrect from situation, when directory /var/lib/rhsm/cache
        does not exist
        """
        # Delete the temporary directory
        os.rmdir(self.temp_cache_dir)

        consumer_uuid = "something"
        synced_store = SyncedStore(self.uep, consumer_uuid=consumer_uuid)
        local_content = self.assertRaisesNothing(synced_store.get_local_contents)
        self.assertEqual(local_content, {})

        # Make sure that the directory was created
        res = os.path.isdir(self.temp_dir)
        self.assertTrue(res)


class TestDetectChange(SyspurposeTestBase):

    def test_added(self):
        """
        Shows that when a key is added to the other dictionary that the result is ChangeType.Added
        """
        key = "a"
        value = "value"
        base = {}
        other = {key: value}

        result = detect_changed(base=base, other=other, key=key)

        self.assertEqual(result, True)

    def test_removed(self):
        """
        Shows that when a key is removed from the other dict that the result is ChangeType.REMOVED
        """
        key = "a"
        value = "value"
        base = {key: value}
        other = {key: None}

        result = detect_changed(base=base, other=other, key=key)
        # For a source of "server" we should not consider the removal a change if the value is None
        self.assertEqual(result, True)

        result = detect_changed(base=base, other=other, key=key, source="local")
        # For a source of "local" we should consider the removal a change
        self.assertEqual(result, True)

    def test_absence_of_field_means_no_change(self):
        """
        Shows when the server does not support a particular type of field, local controls it.
        """
        key = "a"
        value = "value"
        base = {key: value}
        other = {}

        result = detect_changed(base=base, other=other, key=key)

        self.assertEqual(result, UNSUPPORTED)

    def test_changed(self):
        """
        Shows that when a key is changed from the other dict that the result is ChangeType.CHANGED
        """
        key = "a"
        value = "value"
        next_value = "next_value"
        base = {key: value}
        other = {key: next_value}

        result = detect_changed(base=base, other=other, key=key)

        self.assertEqual(result, True)

    def test_lists_out_of_order(self):
        """
        Shows that when two lists are out of order but contain the same elements it is not
        considered a change.
        """
        key = "a"
        value = ["value1", "value2"]
        next_value = value[::-1]
        base = {key: value}
        other = {key: next_value}

        result = detect_changed(base=base, other=other, key=key)

        self.assertEqual(result, False)

    def test_same(self):
        """
        Shows that when a key is the same as in the other dict that the result is ChangeType.SAME.
        """
        key = "a"
        value = "value"
        base = {key: value}
        other = {key: value}

        result = detect_changed(base=base, other=other, key=key)

        self.assertEqual(result, False)

    def test_same_empty(self):
        """
        Shows that when a key is not in either other or base the result is ChangeType.SAME
        """
        key = "a"
        non_existant_key = "b"
        value = "value"
        next_value = "next_value"
        base = {key: value}
        other = {key: next_value}

        result = detect_changed(base=base, other=other, key=non_existant_key, source='server')

        self.assertEqual(result, UNSUPPORTED)

        result = detect_changed(base=base, other=other, key=non_existant_key, source='local')

        self.assertEqual(result, False)


class TestThreeWayMerge(SyspurposeTestBase):

    def test_all_empty(self):
        base = {}
        remote = {}
        local = {}

        expected = {}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_empty_base_no_conflict(self):
        base = {}
        remote = {
            "A": "remote",
            "B": None,
        }
        local = {
            "A": None,
            "B": "local",
        }

        expected = {"A": "remote", "B": "local"}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_local_only(self):
        base = {}
        remote = {"B": None}
        local = {"B": "local"}

        expected = local
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_remote_only(self):
        base = {}
        remote = {"A": "remote"}
        local = {"A": None}

        expected = remote
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_key_removed_no_conflict(self):
        base = {"C": "base"}
        remote = {"C": None}
        local = {"C": None}

        expected = {"C": None}  # C should have the None value
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_key_removed_remote_not_in_base(self):
        base = {}
        remote = {}
        local = {"C": "local"}

        expected = local  # Expect Local to win
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_key_no_longer_supported_from_remote(self):
        base = {"C": "base"}
        remote = {}
        local = {"C": "base"}

        expected = local
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_key_unset_from_remote_with_false_value(self):
        base = {"C": "base"}
        remote = {"C": None}
        local = {"C": "base"}

        expected = {"C": None}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_key_removed_from_local(self):
        base = {"C": "base"}
        remote = {"C": "base"}
        local = {"C": None}

        expected = {"C": None}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

        # Now with the on_conflict param set to "local"

        expected = {"C": None}
        result = three_way_merge(local=local, base=base, remote=remote, on_conflict="local")
        self.assert_equal_dict(expected, result)

    def test_merge_no_potential_conflict(self):
        base = {"C": "base"}
        # A key included from candlepin with a falsey value means that the key is supported, but
        # that there is no value presently set for it.
        remote = {"A": "remote", "B": None, "C": "base"}
        local = {"B": "local", "C": "base"}

        expected = {"A": "remote", "B": "local", "C": "base"}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_merge(self):
        """
        Shows that a change in only one place does not consitute a conflict.
        """
        base = {"C": "base"}
        remote = {"A": "remote", "C": "remote"}
        local = {"B": "local", "C": "base"}

        expected = {"A": "remote", "B": "local", "C": "remote"}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

        # Now with local as the on_conflict winner
        expected = {"A": "remote", "B": "local", "C": "remote"}
        result = three_way_merge(local=local, base=base, remote=remote, on_conflict="local")
        self.assert_equal_dict(expected, result)

    def test_concurrent_modification(self):
        """
        This test shows that remote wins by default in the case of concurrent modification of
        a shared key. It also shows that the on_conflict kwarg can override this.
        """
        shared_key = "C"
        base = {shared_key: "base"}
        # Here the key "C" is changed from "base" to "remote" for remote and to "local" for local
        remote = {"A": "remote", "B": None, shared_key: "remote"}
        local = {"B": "local", shared_key: "local"}

        expected = {"A": "remote", "B": "local", shared_key: "remote"}

        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

        # Now with local set to win
        expected = {"A": "remote", "B": "local", shared_key: "local"}
        result = three_way_merge(local=local, base=base, remote=remote, on_conflict="local")
        self.assert_equal_dict(expected, result)

    def test_concurrent_modification_key_added(self):
        """
        This test shows that remote wins by default in the case of concurrent modification of
        a shared key even when the shared key is not in the base.
        It also shows that the on_conflict kwarg can override this.
        """
        shared_key = "C"
        base = {}
        # Here the key "C" is changed from "base" to "remote" for remote and to "local" for local
        remote = {"A": "remote", "B": None, shared_key: "remote"}
        local = {"B": "local", shared_key: "local"}

        expected = {"A": "remote", "B": "local", shared_key: "remote"}

        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

        # Now with local set to win
        expected = {"A": "remote", "B": "local", shared_key: "local"}
        result = three_way_merge(local=local, base=base, remote=remote, on_conflict="local")
        self.assert_equal_dict(expected, result)

    def test_merge_conflicting_lists(self):
        """
        This test shows that lists are treated atomically (as in we do not merge differing lists).
        """
        shared_key = "C"
        base = {shared_key: ["base"]}
        # Here the key "C" is changed from "base" to "remote" for remote and to "local" for local
        remote = {"A": "remote", "B": None, shared_key: ["remote"]}
        local = {"B": "local", shared_key: ["local"]}

        expected = {"A": "remote", "B": "local", shared_key: ["remote"]}
        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

        # Now with local set to win
        expected = {"A": "remote", "B": "local", shared_key: ["local"]}
        result = three_way_merge(local=local, base=base, remote=remote, on_conflict="local")
        self.assert_equal_dict(expected, result)

    def test_invalid_on_conflict_value(self):
        self.assertRaises(ValueError, three_way_merge, local={}, base={}, remote={},
                          on_conflict="oops")

    def test_merge_remote_missing_field(self):
        """
        Shows that if the server does not support a field, local gets to modify it.
        """
        base = {"B": None}
        remote = {}
        local = {"B": "local"}

        expected = {"B": "local"}

        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_merge_remote_empty_field(self):
        """
        Shows that if the server has field with empty string, local gets to modify it.
        """
        base = {"B": None}
        remote = {"B": ""}
        local = {"B": "local"}

        expected = {"B": "local"}

        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)

    def test_merge_missing_remote_list(self):
        """
        Shows that if the server does not have list, local can add it.
        """
        base = {"B": None}
        remote = {}
        local = {"B": ["local"]}

        expected = {"B": ["local"]}

        result = three_way_merge(local=local, base=base, remote=remote)
        self.assert_equal_dict(expected, result)
