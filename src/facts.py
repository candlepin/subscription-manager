


import glob
import os
import simplejson as json

import config
import hwprobe

factsObj = None

def getFacts():
    global factsObj
    if factsObj:
        return factsObj
    factsObj = Facts()
    return factsObj

class Facts():
    def __init__(self):
        self.facts = {}
        self.fact_cache_dir = "/var/lib/rhsm/facts"
        self.fact_cache = self.fact_cache_dir + "/facts.json"

    def write(self, facts, path="/var/lib/rhsm/facts/facts.json"):
        if not os.access(self.fact_cache_dir, os.R_OK):
            os.makedirs(self.fact_cache_dir)
        try:
            f = open(path, "w+")
            json.dump(facts, f)
        except IOError, e:
            print e

    def read(self,  path="/var/lib/rhsm/facts/facts.json"):
        cached_facts = {}
        try:
            f = open(path)
            json_buffer = f.read()
            cached_facts = json.loads(json_buffer)
        except IOError, e:
            print "Unable to read %s" % path

        return cached_facts

    # return a dict of any key/values that have changed
    # including new keys or deleted keys
    def delta(self):
        cached_facts = self.read(self.fact_cache)
        diff = {}
        self.facts = self.get_facts()
        # compare the dicts to see if there is a diff

        for key in self.facts:
            value = self.facts[key]
            # new fact found
            if key not in cached_facts:
                diff[key] = value
            if key in cached_facts:
                # key changed values
                if value != cached_facts[key]:
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
        self.facts =  self.find_facts()
        return self.facts

    def find_facts(self):
        # don't figure this out twice if we already did it for
        # delta()
        facts_file_glob = "%s/facts/*.facts" % config.DEFAULT_CONFIG_DIR
    
        file_facts = {}
        for file_path in glob.glob(facts_file_glob):
            if os.access(file_path, os.R_OK):
                f = open(file_path)
                json_buffer = f.read()
                file_facts.update(json.loads(json_buffer))
    
        facts ={}
        hw_facts = hwprobe.Hardware().getAll()
        
        facts.update(hw_facts)
        facts.update(file_facts)
#        pprint.pprint(facts)

        self.write(facts)
        return facts

