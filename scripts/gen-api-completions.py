#!/usr/bin/python

# Copyright 2013 Red Hat
#
# Generate a txt file of candlepin api method paths (ie,
# /consumers/{consumer_uuid}) from api docs
#
#  ./gen-api-completions.py candlepin_methods.json
#
# for example, the data from https://github.com/RoUS/candlepin-api
# or the candlepin api docs generated with:
#
#  cd ~/src/candlepin/server
#  buildr candlepin:server:apicrawl
#
# api info is written to candlepin/server/target/candlepin_methods.json
#

import simplejson as json
import sys
from collections import defaultdict


def find_verb(verb, api):
    return [x for x in api if verb in x['httpVerbs']]


def find_verbs(verb_map, api):
    for method in api:
        verb_list = method['httpVerbs']
        for verb in verb_list:
            verb_map[verb].append(method)
    return verb_map


def method_paths(method_list):
    return [x['url'] for x in method_list]


def write_completions(verb, method_list):
    completions_filename = "candlepin-api-completions-%s" % verb
    completions_fp = open(completions_filename, 'w')
    paths = method_paths(method_list)
    completions_fp.write('\n'.join(paths))
    completions_fp.close()


def main():
    api_json_filename = sys.argv[1]
    api_json_fp = open(api_json_filename, 'r')

    api = json.load(api_json_fp)

    verb_map = defaultdict(list)

    #pprint.pprint([(x['url'], x['verifiedParams']) for x in api])

    verb_map = find_verbs(verb_map, api)

    all_paths = []
    for verb in verb_map:
        all_paths += method_paths(verb_map[verb])
        #write_completions(verb, verb_map[verb])

    completions = sorted(set(all_paths))
    for completion in completions:
        print completion

if __name__ == "__main__":
    main()
