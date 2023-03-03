# Copyright (c) 2016 Red Hat, Inc.
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
import logging
import os
import platform
from typing import Callable, Dict, List, Union

from rhsmlib.facts import collection

log = logging.getLogger(__name__)


def get_arch(prefix: str = None) -> str:
    """Get the systems architecture.

    This relies on portable means, like uname to determine
    a high level system arch (ie, x86_64, ppx64,etc).

    We need that so we can decide how to collect the
    arch specific hardware information.

    Also support a 'prefix' arg that allows us to override
    the results. The contents of the '/prefix/arch' will
    override the arch. The 'prefix' arg defaults to None,
    equiv to '/'. This is intended only for test purposes.

    Returns a string containing the arch."""

    DEFAULT_PREFIX = "/"
    ARCH_FILE_NAME = "arch"
    prefix = prefix or DEFAULT_PREFIX

    if prefix == DEFAULT_PREFIX:
        return platform.machine()

    arch_file: str = os.path.join(prefix, ARCH_FILE_NAME)
    try:
        with open(arch_file, "r") as arch_fd:
            return arch_fd.read().strip()
    except IOError as e:
        # If we specify a prefix, and there is no 'arch' file,
        # consider that fatal.
        log.exception(e)
        raise


# An empty FactsCollector should just return an empty dict on get_all()


class FactsCollector:
    def __init__(
        self,
        arch: str = None,
        prefix: str = None,
        testing: bool = None,
        hardware_methods: List[Callable] = None,
        collected_hw_info: Dict[str, Union[str, int, bool, None]] = None,
    ):
        """Base class for facts collecting classes.

        self._collected_hw_info will reference the passed collected_hw_info
        arg. When possible this should be a reference (or copy) to all of the facts
        collected in this run. Some collection methods need to alter behavior
        based on facts collector from other modules/classes.
        self._collected_hw_info isn't meant to be altered as a side effect, but
        no promises."""
        self.allhw: Dict[str, Union[str, int, bool, None]] = {}
        self.prefix: str = prefix or ""
        self.testing: bool = testing or False

        self._collected_hw_info: Dict[str, Union[str, int, bool, None]] = collected_hw_info
        # we need this so we can decide which of the
        # arch specific code bases to follow
        self.arch: str = arch or get_arch(prefix=self.prefix)

        self.hardware_methods: List[Callable] = hardware_methods or []

    def collect(self) -> collection.FactsCollection:
        """Return a FactsCollection iterable."""
        facts_dict = collection.FactsDict()
        facts_dict.update(self.get_all())
        facts_collection = collection.FactsCollection(facts_dict=facts_dict)
        return facts_collection

    def get_all(self) -> Dict[str, Union[str, int, bool, None]]:
        # try each hardware method, and try/except around, since
        # these tend to be fragile
        all_hw_info: Dict[str, Union[str, int, bool, None]] = {}
        for hardware_method in self.hardware_methods:
            info_dict: Dict[str, Union[str, int, bool, None]] = {}
            try:
                info_dict = hardware_method()
            except Exception as e:
                log.warning("Hardware detection [%s] failed: %s" % (hardware_method.__name__, e))

            all_hw_info.update(info_dict)

        return all_hw_info


class StaticFactsCollector(FactsCollector):
    def __init__(self, static_facts: Dict[str, str] = None, **kwargs):
        super(StaticFactsCollector, self).__init__(**kwargs)
        if static_facts is None:
            static_facts: Dict[str, str] = {}
        self.static_facts = static_facts
        self.static_facts.setdefault("system.certificate_version", "3.2")

    def get_all(self) -> Dict[str, str]:
        return self.static_facts
