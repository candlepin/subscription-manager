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

import glob
import os
import simplejson as json
import logging
import gettext
_ = gettext.gettext

import rhsm.config
from subscription_manager import certdirectory
from subscription_manager import cert_sorter
from subscription_manager.cache import CacheManager
from subscription_manager.hwprobe import ClassicCheck
from datetime import datetime

log = logging.getLogger('rhsm-app.' + __name__)


class Facts(CacheManager):
    """
    Manages the facts for this system, maintains a cache of the most
    recent set sent to server, and checks for changes.

    Includes both those hard coded in the app itself, as well as custom
    facts to be loaded from /etc/rhsm/facts/.
    """
    CACHE_FILE = "/var/lib/rhsm/facts/facts.json"

    def __init__(self, ent_dir=None, prod_dir=None):
        self.facts = {}

        self.entitlement_dir = ent_dir or certdirectory.EntitlementDirectory()
        self.product_dir = prod_dir or certdirectory.ProductDirectory()
        # see bz #627962
        # we would like to have this info, but for now, since it
        # can change constantly on laptops, it makes for a lot of
        # fact churn, so we report it, but ignore it as an indicator
        # that we need to update
        self.graylist = ['cpu.cpu_mhz']

    def get_last_update(self):
        try:
            return datetime.fromtimestamp(os.stat(self.CACHE_FILE).st_mtime)
        except:
            return None

    def has_changed(self):
        """
        return a dict of any key/values that have changed
        including new keys or deleted keys
        """
        cached_facts = self._read_cache()
        diff = {}
        self.facts = self.get_facts()
        # compare the dicts to see if there is a diff

        for key in self.facts:
            value = self.facts[key]
            # new fact found
            if key not in cached_facts:
                diff[key] = value
            if key in cached_facts:
                # key changed values, ignore changes in graylist facts
                if value != cached_facts[key] and key not in self.graylist:
                    diff[key] = value

        # look for keys that went away
        for key  in cached_facts:
            if key not in self.facts:
                #update with new value, though it doesnt matter
                diff[key] = cached_facts[key]

        return len(diff) > 0

    def get_facts(self):
        if self.facts:
            # see bz #627707
            # there is a little bit of a race between when we load the facts, and when
            # we decide to save them, so delete facts out from under a Fact object means
            # it wasn't detecting it missing in that case and not writing a new one
            return self.facts
        self.facts = self._load_custom_facts()
        return self.facts

    def to_dict(self):
        return self.get_facts()

    def _load_custom_facts(self):
        """
        Load custom facts from .facts files in /etc/rhsm/facts.
        """
        facts_file_glob = "%s/facts/*.facts" % rhsm.config.DEFAULT_CONFIG_DIR
        file_facts = {}
        for file_path in glob.glob(facts_file_glob):
            if os.access(file_path, os.R_OK):
                f = open(file_path)
                json_buffer = f.read()
                file_facts.update(json.loads(json_buffer))

        facts = {}
        import hwprobe
        hw_facts = hwprobe.Hardware().getAll()

        facts.update(hw_facts)
        facts.update(file_facts)

        # fact collection should probably become "pluggable" at some
        # point

        # figure out if we think we have valid entitlements
        validity_facts = self._get_validity_facts(facts)

        facts.update(validity_facts)

        return facts


    def _get_validity_facts(self, facts):
        validity_facts = {'system.entitlements_valid': 'valid'}
        if not ClassicCheck().is_registered_with_classic():
            sorter = cert_sorter.CertSorter(self.product_dir,
                                            self.entitlement_dir,
                                            facts_dict=facts)
            if (len(sorter.partially_valid_products) > 0):
                validity_facts['system.entitlements_valid'] = 'partial'

            if ((len(sorter.expired_entitlement_certs) +
                len(sorter.unentitled_products)) > 0):
                validity_facts['system.entitlements_valid'] = 'invalid'

        return validity_facts

    def _update_server(self, uep, consumer_uuid):
        uep.updateConsumer(consumer_uuid, facts=self.get_facts())

    def _load_data(self, open_file):
        json_str = open_file.read()
        return json.loads(json_str)
