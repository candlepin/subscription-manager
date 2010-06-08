

import glob
import os
import sys
import simplejson as json


import config
import hwprobe

def get_facts():
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

    return facts
