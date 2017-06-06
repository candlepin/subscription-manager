from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 Red Hat, Inc.
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
import logging
import os

from subscription_manager.injection import PLUGIN_MANAGER, require
from subscription_manager.cache import CacheManager
from rhsm import ourjson as json

from rhsmlib.facts.all import AllFactsCollector

log = logging.getLogger(__name__)


class Facts(CacheManager):
    """
    Manages the facts for this system, maintains a cache of the most
    recent set sent to server, and checks for changes.

    Includes both those hard coded in the app itself, as well as custom
    facts to be loaded from /etc/rhsm/facts/.
    """
    CACHE_FILE = "/var/lib/rhsm/facts/facts.json"

    def __init__(self):
        self.facts = {}

        # see bz #627962
        # we would like to have this info, but for now, since it
        # can change constantly on laptops, it makes for a lot of
        # fact churn, so we report it, but ignore it as an indicator
        # that we need to update
        self.graylist = ['cpu.cpu_mhz', 'lscpu.cpu_mhz']

        # plugin manager so we can add custom facts via plugin
        self.plugin_manager = require(PLUGIN_MANAGER)

    def get_last_update(self):
        try:
            return datetime.fromtimestamp(os.stat(self.CACHE_FILE).st_mtime)
        except Exception:
            return None

    def has_changed(self):
        """
        return a dict of any key/values that have changed
        including new keys or deleted keys
        """
        if not self._cache_exists():
            log.debug("Cache %s does not exit" % self.CACHE_FILE)
            return True

        cached_facts = self.read_cache_only() or {}
        # In order to accurately check for changes, we must refresh local data
        self.facts = self.get_facts(True)

        for key in (set(self.facts) | set(cached_facts)) - set(self.graylist):
            if self.facts.get(key) != cached_facts.get(key):
                return True
        return False

    def get_facts(self, refresh=False):
        if len(self.facts) == 0 or refresh:
            collector = AllFactsCollector()
            facts = collector.get_all()
            self.plugin_manager.run('post_facts_collection', facts=facts)
            self.facts = facts
        return self.facts

    def to_dict(self):
        return self.get_facts()

    def _sync_with_server(self, uep, consumer_uuid):
        log.debug("Updating facts on server")
        uep.updateConsumer(consumer_uuid, facts=self.get_facts())

    def _load_data(self, open_file):
        json_str = open_file.read()
        return json.loads(json_str)
