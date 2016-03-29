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


class FactsCollection(object):
    def __init__(self, facts_dict=None, expiration=None):
        """expiration needs to be a FactsCollectionExpiration like instance.

        Not providing one means the FactsCollection has an infinite expiration
        and will never expire."""

        self.data = facts_dict or FactsDict()
        self.expiration = expiration

        # If the cache has been persisted, or doesn't need to be persisted
        # then dirty = False
        self.dirty = False

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
        # The FactsCollector subclass needs to set dirty in it's init.
        # Here, we don't need to be persisted, so dirty is by default False.
        log.debug("FC.from_facts_collection fc=%s", fc)
        return fc

    @classmethod
    def from_cache(cls, cache):
        """Create a FactsCollection from a Cache object.

        Any errors reading the Cache can raise CacheError exceptions."""
        log.debug("FC.from_cache")
        fc = cls(cache.read(), cache.expiration)
        fc.dirty = False
        return fc

    def cache_save_start(self, facts_collection):
        # Create a new FactsCollection with new timestamp
        log.debug("save_to_cache facts_collection=%s", facts_collection)
        # We are not persisted, nothing to do.
        self.cache_save_finished(facts_collection)

    def cache_save_finished(self, facts_collection):
        # Set dirty flag to False, though non-persistent classes are always False
        self.dirty = False

    def merge(self, other):
        """Combine a cached collection and a fresh collection according to caching rules."""
        if other is None:
            return self

        if not hasattr(other, 'data'):
            return self

        # If current time isn't within either collections valid lifetime, they are
        # not equals
        if self.expired() and other.expired():
            log.debug("FactsCollection cache expire for %s and %s", self, other)
            raise Exception("Both facts collections are expired and invalid: %s and %s", self, other)

        if self.expired():
            other.dirty = True
            return other

        # We are not expired and that is all that matters.
        return self

    def __iter__(self):
        return self.data

    def expired(self):
        """Check expiration for expired, no expiration means expired() is never True."""
        if self.expiration:
            return self.expiration.expired()
        return False
