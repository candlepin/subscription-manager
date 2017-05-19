from __future__ import print_function, division, absolute_import

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

from rhsmlib.facts import collection

log = logging.getLogger(__name__)


def get_arch(prefix=None):
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

    DEFAULT_PREFIX = '/'
    ARCH_FILE_NAME = 'arch'
    prefix = prefix or DEFAULT_PREFIX

    if prefix == DEFAULT_PREFIX:
        return platform.machine()

    arch_file = os.path.join(prefix, ARCH_FILE_NAME)
    try:
        with open(arch_file, 'r') as arch_fd:
            return arch_fd.read().strip()
    except IOError as e:
        # If we specify a prefix, and there is no 'arch' file,
        # consider that fatal.
        log.exception(e)
        raise

# An empty FactsCollector should just return an empty dict on get_all()


class FactsCollector(object):
    def __init__(self, arch=None, prefix=None, testing=None,
                 hardware_methods=None, collected_hw_info=None):
        """Base class for facts collecting classes.

        self._collected_hw_info will reference the passed collected_hw_info
        arg. When possible this should be a reference (or copy) to all of the facts
        collected in this run. Some collection methods need to alter behavior
        based on facts collector from other modules/classes.
        self._collected_hw_info isn't meant to be altered as a side effect, but
        no promises."""
        self.allhw = {}
        self.prefix = prefix or ''
        self.testing = testing or False

        self._collected_hw_info = collected_hw_info
        # we need this so we can decide which of the
        # arch specific code bases to follow
        self.arch = arch or get_arch(prefix=self.prefix)

        self.hardware_methods = hardware_methods or []

    def collect(self):
        """Return a FactsCollection iterable."""
        facts_dict = collection.FactsDict()
        facts_dict.update(self.get_all())
        facts_collection = collection.FactsCollection(facts_dict=facts_dict)
        return facts_collection

    def get_all(self):
        # try each hardware method, and try/except around, since
        # these tend to be fragile
        all_hw_info = {}
        for hardware_method in self.hardware_methods:
            info_dict = {}
            try:
                info_dict = hardware_method()
            except Exception as e:
                log.warn("Hardware detection [%s] failed: %s" % (hardware_method.__name__, e))

            all_hw_info.update(info_dict)

        return all_hw_info


class StaticFactsCollector(FactsCollector):
    def __init__(self, static_facts=None, **kwargs):
        super(FactsCollector, self).__init__(**kwargs)
        if static_facts is None:
            static_facts = {}
        self.static_facts = static_facts
        self.static_facts.setdefault("system.certificate_version", "3.2")

    def get_all(self):
        return self.static_facts
