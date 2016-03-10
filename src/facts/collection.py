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

import collections
import datetime
import functools
import itertools


# TODO: Likely a bit much for this case
@functools.total_ordering
class FactsDict(collections.MutableMapping):
    """A dict for facts that ignores items in 'graylist' on compares."""

    graylist = ['cpu.cpu_mhz', 'lscpu.cpu_mhz']

    def __init__(self, *args, **kwargs):
        super(FactsDict, self).__init__(*args, **kwargs)
        self.data = {}
        self.gray_data = {}

    def __missing__(self, key):
        # If key is not found in data, try self.gray_data, if still missing key error
        return self.gray_data[key]

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        if key in self.graylist:
            self.gray_data[key] = value
        else:
            self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return itertools.chain(self.data,
                               self.gray_data)
        #return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        """Compares all of the items in self.data, except it ignores keys in self.graylist."""
        try:
            return dict(self.data.items()) == dict(other.data.items())
        except AttributeError:
            return False

    # Maybe total_ordering is a bit overkill for just a custom compare
    def __lt__(self, other):
        return len(self.data) < len(other.data)

# Support a @from_previous_collection could also populate a list/map of changed facts...


@functools.total_ordering
class FactsCollection(object):
    def __init__(self, facts_dict=None, collection_datetime=None, cache_lifetime=None):
        self.data = facts_dict or FactsDict()
        self.collection_datetime = collection_datetime or datetime.datetime.utcnow()
        # Or just assume we'll get a datetime.timedelta
        self.cache_lifetime = cache_lifetime or 0

    @classmethod
    def from_facts_collection(cls, facts_collection):
        """Create a FactsCollection with the data from facts_collection, but new timestamps.

        ie, a copy(), more or less."""
        fc = cls()
        fc.data.update(facts_collection.data)
        return fc

    @classmethod
    def from_cache(cls, cache, cache_lifetime=None):
        """Create a FactsCollection from a Cache object.

        Any errors reading the Cache can raise CacheError exceptions."""
        return cls(cache.read(), cache.timestamp, cache_lifetime)

    @property
    def expiry_datetime(self):
        return self.collection_datetime + datetime.timedelta(seconds=self.cache_lifetime)

    def __eq__(self, other):
        if other is None:
            return False

        if not hasattr(other, 'data'):
            return False

        # If current time isn't within either collections valid lifetime, they are
        # not equals
        if any(self.expired(), other.expired()):
            return False

        return True

    def __iter__(self):
        return self.data
        #return iter(self.data)

    # cached_valid_facts_set_b = ()
    # cached_valid_facts_set_a
    # cached_expired_facts =
    # just_born_facts_set_a = b
    # just_born_facts_set_c
    # just_born_expired_facts == ...?
    #
    # cached_valid_facts_set_a == just_born_facts_set_a        True
    # cached_valid_facts_set_a != just_born_facts_set_a        False
    # cached_valid_facts_set_a == cached_valid_facts_set_b     True
    # cached_valid_facts_set_a > cached_valid_facts_set_b      False
    # cached_valid_facts_set_a >= cached_valid_facts_set_b     True
    # cached_valid_facts_set_a < cached_valid_facts_set_b      False
    # cached_valid_facts_set_a <= cached_valid_facts_set_b     True
    # cached_valid_facts_set_a != cached_valid_facts_set_b     True
    # cached_valid_facts_set_a > just_born_facts_set_a         False
    # just_born_facts_set_a > cached_valid_facts_set_a         True
    # cached_valid_facts_set_a >= just_born_facts_set_a        True
    # just_born_facts_set_a >= cached_valid_facts_set_a        True

    def __ne__(self, other):
        if other is None:
            return True

        # If current time isn't within either collections valid lifetime, they are
        # not equals
        if any(self.expired(), other.expired()):
            return False

        return self.data != other.data

    def expired(self, at_time=None):
        at_time = at_time or datetime.datetime.utcnow()
        return self.expiry_datetime > at_time

    def __gt__(self, other):
        # type check?
        # expiring/expired at later date then other is greater
        if self == other:
            return False
        return self.expiry_datetime > other.expiry_datetime

    def __gte__(self, other):
        if self == other:
            return True
        return self.expiry_datetime >= other.expiry_datetime
