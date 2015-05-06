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

from gi.repository import Gtk
import logging


class MappedStore(object):
    def __init__(self, type_map):
        self.type_index = {}
        self.log = logging.getLogger('rhsm-app.' + __name__ +
                                     self.__class__.__name__)

        # Enumerate the keys and store the int index
        for i, type_key in enumerate(type_map.iterkeys()):
            self.type_index[type_key] = i

    def _create_initial_entry(self, item_map):
        """
        Initialize the entry - this way the map does not have to
        specify all keys, and a 'None' value is inserted by default into
        positions that are omitted
        """

        # get_n_columns() is 0 if the subclasses Gtk.ListStore isn't
        # init'ed first, since no column info is known
        entry = [None] * self.get_n_columns()

        for key, value in item_map.iteritems():
            entry[self[key]] = value
        return entry

    def __contains__(self, item):
        return item in self.type_index


# FIXME: There isn't much reason to make the MappedStores inherit MappedStore
#        it could just have-a MappedStore
class MappedListStore(MappedStore, Gtk.ListStore):

    def __init__(self, type_map):
        """
        Create a new list store from the given type_map, which is a dictionary
        in the format type_map[identifier] = type - where 'identifier' is a
        string that identifies the item and 'type' is a gobject type or some
        built-in python type that is suitable for conversion to a gobject type.

        See contructor for Gtk.ListStore.
        """

        # FIXME: this is fragile, since the .values() ordering is not reliable
        MappedStore.__init__(self, type_map)
        Gtk.ListStore.__init__(self, *type_map.values())
        # Use the types from the map to call the parent constructor

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
        self.append(self._create_initial_entry(item_map))


class MappedTreeStore(MappedStore, Gtk.TreeStore):
    def __init__(self, type_map):
        self.log = logging.getLogger('rhsm-app.' + __name__ +
                                     self.__class__.__name__)
        # FIXME: How does this work? .values() is not sorted, so could change?
        MappedStore.__init__(self, type_map)
        Gtk.TreeStore.__init__(self, *type_map.values())

    def __getitem__(self, key):
        return self.type_index[key]

    def add_map(self, tree_iter, item_map):
        return self.append(tree_iter,
                           self._create_initial_entry(item_map))
