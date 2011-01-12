import glob
import os
import simplejson as json
import gettext
_ = gettext.gettext

import rhsm.config

from datetime import datetime

class Facts():

    def __init__(self):
        self.facts = {}
        self.fact_cache_dir = "/var/lib/rhsm/facts"
        self.fact_cache = self.fact_cache_dir + "/facts.json"

        # see bz #627962
        # we would like to have this info, but for now, since it
        # can change constantly on laptops, it makes for a lot of
        # fact churn, so we report it, but ignore it as an indicator
        # that we need to update
        self.graylist = ['cpu.cpu_mhz']

    def write(self, facts, force=False):
        if not os.access(self.fact_cache_dir, os.R_OK):
            os.makedirs(self.fact_cache_dir)
        try:
            existing_facts = self.read()

            if force or facts != existing_facts:
                f = open(self.fact_cache, "w+")
                json.dump(facts, f)
        except IOError, e:
            print e

    def read(self):
        cached_facts = {}
        try:
            f = open(self.fact_cache)
            json_buffer = f.read()
            cached_facts = json.loads(json_buffer)
        except IOError, e:
            print _("Unable to read %s") % self.fact_cache
        except json.decoder.JSONDecodeError:
            # no need to show the user, they can't really do
            # anything about it, and we ignore it otherwise
            # see bz #667953
            pass

        return cached_facts

    def get_last_update(self):
        try:
            return datetime.fromtimestamp(os.stat(self.fact_cache).st_mtime)
        except:
            return None

    def delta(self):
        """
        return a dict of any key/values that have changed
        including new keys or deleted keys
        """
        cached_facts = self.read()
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

        return diff

    def get_facts(self):
        if self.facts:
            # see bz #627707
            # there is a little bit of a race between when we load the facts, and when
            # we decide to save them, so delete facts out from under a Fact object means
            # it wasn't detecting it missing in that case and not writing a new one
            self.write(self.facts)
            return self.facts
        self.facts = self.find_facts()
        return self.facts

    def find_facts(self):
        # don't figure this out twice if we already did it for
        # delta()
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
#        pprint.pprint(facts)

        self.write(facts)
        return facts

