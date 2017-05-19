from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
from datetime import datetime
import collections
import logging

log = logging.getLogger(__name__)


# TODO: Likely a bit much for this case
class FactsDict(collections.MutableMapping):
    """A dict for facts that ignores items in 'graylist' on compares."""

    graylist = set(['cpu.cpu_mhz', 'lscpu.cpu_mhz'])

    def __init__(self, *args, **kwargs):
        super(FactsDict, self).__init__(*args, **kwargs)
        self.data = {}

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        """Compares all of the items in self.data, except it ignores keys in self.graylist."""
        if not isinstance(other, FactsDict):
            return NotImplemented

        keys_self = set(self.data).difference(self.graylist)
        keys_other = set(other.data).difference(self.graylist)
        if keys_self == keys_other:
            if all(self.data[k] == other.data[k] for k in keys_self):
                return True

        return False

    # Maybe total_ordering is a bit overkill for just a custom compare
    def __lt__(self, other):
        return len(self) < len(other)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self.items()))


def compare_with_graylist(dict_a, dict_b, graylist):
    ka = set(dict_a).difference(graylist)
    kb = set(dict_b).difference(graylist)
    return ka == kb and all(dict_a[k] == dict_b[k] for k in ka)


class FactsCollection(object):
    def __init__(self, facts_dict=None):
        self.data = facts_dict or FactsDict()
        self.collection_datetime = datetime.now()

    def __repr__(self):
        buf = "%s(facts_dict=%s, collection_datetime=%s)" % \
            (self.__class__.__name__, self.data, self.collection_datetime)
        return buf

    @classmethod
    def from_facts_collection(cls, facts_collection):
        """Create a FactsCollection with the data from facts_collection, but new timestamps.
        ie, a copy(), more or less."""
        fc = cls()
        fc.data.update(facts_collection.data)
        return fc

    def __iter__(self):
        return self.data
