import datetime

# semi-opaque wrapper for 'just the facts' and the metadata associated with it


# FIXME: have to find better names...
class Facts(object):
    def __init__(self, facts_dict=None, collection_timestamp=None, cache_lifetime=None):
        self.data = facts_dict or {}
        #                                                                   UtcNow? FIXME
        self.collection_timestamp = collection_timestamp or datetime.datetime.Now()
        self.cache_lifetime = cache_lifetime or 0

    def __ne__(self, other):
        if other is None:
            return True

        # debatable...
        if not isinstance(other, Facts):
            return True

        if not hasattr(other, 'data'):
            return True

        if self.compare_meta(self.data, other.data):
            return True

        if self.compare_data(self.data, other.data):
            return True

    def compare_meta(self, our_data, other, data):
        # er... compare the cache expires, probably better
        # as a __gt__/__lt__
        pass

    def compare_data(self, our_data, other_data):
        pass
        # could be fancy...
        #return our_data != other_data

        # but likely need to compare the hashes
        #
        # sorta, sans graylist
        # if len(our_data) != len(other_data):
        #      return True
        #
        # convert into sets/tuples, sort on key
        # if sorted(set(our_data.items())) != sorted(set(other_data.items())):
        #      return True
