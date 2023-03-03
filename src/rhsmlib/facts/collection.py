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
import collections.abc
import logging
from typing import Any, Iterator, Dict, Set

log = logging.getLogger(__name__)


# TODO: Likely a bit much for this case
class FactsDict(collections.abc.MutableMapping):
    """A dict for facts that ignores items in 'graylist' on compares."""

    graylist = set(["cpu.cpu_mhz", "lscpu.cpu_mhz"])

    def __init__(self, *args, **kwargs):
        super(FactsDict, self).__init__(*args, **kwargs)
        self.data: Dict[str, Any] = {}

    def __getitem__(self, key) -> Any:
        return self.data[key]

    def __setitem__(self, key, value) -> None:
        self.data[key] = value

    def __delitem__(self, key) -> None:
        del self.data[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other) -> bool:
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
    def __lt__(self, other) -> bool:
        return len(self) < len(other)

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, list(self.items()))


def compare_with_graylist(dict_a: dict, dict_b: dict, graylist: Set[str]) -> bool:
    ka = set(dict_a).difference(graylist)
    kb = set(dict_b).difference(graylist)
    return ka == kb and all(dict_a[k] == dict_b[k] for k in ka)


class FactsCollection:
    def __init__(self, facts_dict: FactsDict = None):
        self.data: FactsDict = facts_dict or FactsDict()
        self.collection_datetime = datetime.now()

    def __repr__(self) -> str:
        buf: str = "%s(facts_dict=%s, collection_datetime=%s)" % (
            self.__class__.__name__,
            self.data,
            self.collection_datetime,
        )
        return buf

    @classmethod
    def from_facts_collection(cls, facts_collection: "FactsCollection") -> "FactsCollection":
        """Create a FactsCollection with the data from facts_collection, but new timestamps.
        ie, a copy(), more or less."""
        fc: FactsCollection = cls()
        fc.data.update(facts_collection.data)
        return fc

    def __iter__(self) -> Iterator:
        return self.data
