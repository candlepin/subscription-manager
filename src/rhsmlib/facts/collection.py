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
import logging

log = logging.getLogger(__name__)


# TODO: Likely a bit much for this case
@functools.total_ordering
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

        log.debug("FactsDict _eq_ %s == %s", self, other)
        keys_self = set(self.data).difference(self.graylist)
        keys_other = set(other.data).difference(self.graylist)
        if keys_self == keys_other:
            if all(self.data[k] == other.data[k] for k in keys_self):
                log.debug("FactsDict %s == %s is true?", self, other)
                return True

        return False

    # Maybe total_ordering is a bit overkill for just a custom compare
    def __lt__(self, other):
        return len(self) < len(other)

# Support a @from_previous_collection could also populate a list/map of changed facts...


def compare_with_graylist(dict_a, dict_b, graylist):
    ka = set(dict_a).difference(graylist)
    kb = set(dict_b).difference(graylist)
    return ka == kb and all(dict_a[k] == dict_b[k] for k in ka)


@functools.total_ordering
class FactsCollection(object):
    def __init__(self, facts_dict=None, collection_datetime=None, cache_lifetime=None):
        self.data = facts_dict or FactsDict()
        self.collection_datetime = collection_datetime or datetime.datetime.utcnow()
        # Or just assume we'll get a datetime.timedelta
        self.cache_lifetime = cache_lifetime or 0
        log.debug("init %s", repr(self.collection_datetime))
        log.debug(self)

    def __repr__(self):
        buf = "%s(facts_dict=%s, collection_datetime=%s, cache_lifetime=%s)" % \
            (self.__class__.__name__, self.data, self.collection_datetime, self.cache_lifetime)
        return buf

    @classmethod
    def from_facts_collection(cls, facts_collection):
        """Create a FactsCollection with the data from facts_collection, but new timestamps.

        ie, a copy(), more or less."""
        fc = cls()
        fc.data.update(facts_collection.data)
        log.debug("FC.from_facts_collection fc=%s", fc)
        return fc

    @classmethod
    def from_cache(cls, cache, cache_lifetime=None):
        """Create a FactsCollection from a Cache object.

        Any errors reading the Cache can raise CacheError exceptions."""
        log.debug("FC.from_cache")
        return cls(cache.read(), cache.timestamp, cache_lifetime)

    @property
    def expiry_datetime(self):
        #log.debug("expiry_datetime")
        return self.collection_datetime + datetime.timedelta(seconds=self.cache_lifetime)

    def __eq__(self, other):
        log.debug("FactsCollection.__eq__ comparing %s == %s", self, other)
        if other is None:
            return False

        if not hasattr(other, 'data'):
            return False

        # If current time isn't within either collections valid lifetime, they are
        # not equals
        if any([self.expired(), other.expired()]):
            log.debug("FactsCollection cache expire for %s and %s", self, other)
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
        log.debug("__ne__ %s != %s", self, other)
        if other is None:
            return True

        # If current time isn't within either collections valid lifetime, they are
        # not equals
        if any(self.expired(), other.expired()):
            log.debug("Not ne, expired...")
            return False

        return self.data != other.data

    def expired(self, at_time=None):
        at_time = at_time or datetime.datetime.utcnow()
        log.debug("Self=%s", self)
        log.debug("FC    expire check expdt=%s at_time=%s", repr(self.expiry_datetime), repr(at_time))
        log.debug("FC    expire check expdt=%s at_time=%s", self.expiry_datetime, at_time)
        log.debug("FC    expire check exp < at_time = %s", self.expiry_datetime < at_time)
        return self.expiry_datetime < at_time

    def __gt__(self, other):
        # type check?
        # expiring/expired at later date then other is greater
        log.debug("_gt_ %s > %s", self, other)
        if self == other:
            return False
        ret = self.expiry_datetime > other.expiry_datetime
        log.debug("_gt_ %s > %s == %s", self.expiry_datetime, other.expiry_datetime)
        return ret

    def __gte__(self, other):
        log.debug("_gte_ %s >= %s", self, other)
        if self == other:
            return True
        ret = self.expiry_datetime >= other.expiry_datetime
        log.debug("_gte_ %s >= %s == %s", self.expiry_datetime, other.expiry_datetime)
        return ret
