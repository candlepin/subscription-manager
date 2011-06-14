#
# Copyright (c) 2010 Red Hat, Inc.
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

import gtk


class MappedListStore(gtk.ListStore):

    def __init__(self, type_map):
        """
        Create a new list store from the given type_map, which is a dictionary
        in the format type_map[identifier] = type - where 'identifier' is a
        string that identifies the item and 'type' is a gobject type or some
        built-in python type that is suitable for conversion to a gobject type.

        See contructor for gtk.ListStore.
        """
        self.type_index = {}

        # Enumerate the keys and store the int index
        for i, type_key in enumerate(type_map.iterkeys()):
            self.type_index[type_key] = i

        # Use the types from the map to call the parent constructor
        super(MappedListStore, self).__init__(*type_map.values())

    def __getitem__(self, key):
        return self.type_index[key]

    def add_map(self, item_map):
        """
        Add an entry to the store, where item_map is a dictionary in the format
        item_map[identifier] = value - where 'identifier' is a string that was
        used as a key in the constructor, and 'value' is the value of that item.

        This method essentially repackages the data into an appropriately ordered
        list to append to the list store.
        """
        # Initialize the entry - this way the map does not have to
        # specify all keys, and a 'None' value is inserted by default into
        # positions that are omitted
        entry = [None for i in range(self.get_n_columns())]

        for key, value in item_map.iteritems():
            entry[self[key]] = value

        self.append(entry)
