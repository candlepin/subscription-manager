# Copyright (c) 2011 Red Hat, Inc.
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

import unittest
from subscription_manager.gui.storage import MappedTreeStore, MappedListStore


class StorageTests(unittest.TestCase):

    def test_mapped_list_store(self):
        self._run_test(MappedListStore, lambda data, store: store.add_map(data))

    def test_mapped_tree_store(self):
        self._run_test(MappedTreeStore, lambda data, store: store.add_map(None, data))

    def _run_test(self, store_class, add_data_to_map_funct):
        expected_c1 = "C1_VAL"
        expected_c2 = True
        expected_c3 = "C3_val"
        store = self.create_store(store_class)
        data = self.create_data_map(expected_c1, expected_c2, expected_c3)
        add_data_to_map_funct(data, store)

        iter = store.get_iter_first()
        self.assertEquals(expected_c1, store.get_value(iter, store['c1']))
        self.assertEquals(expected_c2, store.get_value(iter, store['c2']))
        self.assertEquals(expected_c3, store.get_value(iter, store['c3']))

    def create_store(self, store_class):
        type_map = {
            'c1': str,
            'c2': bool,
            'c3': str
        }

        return store_class(type_map)

    def create_data_map(self, c1_str, c2_bool, c3_str):
        return {
            'c1': c1_str,
            'c2': c2_bool,
            'c3': c3_str
        }
