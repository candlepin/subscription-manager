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
import os
import glob
import logging

import rhsm.config

from rhsm import ourjson
from rhsmlib.facts.collector import FactsCollector

log = logging.getLogger(__name__)


class CustomFacts(object):
    def __init__(self, data=None):
        self.data = data

    @classmethod
    def from_json(cls, json_blob):
        custom_facts = cls

        # Default to no facts collected
        # See BZ#1435771
        data = {}
        try:
            data = ourjson.loads(json_blob)
        except ValueError:
            log.warn("Unable to load custom facts file.")

        custom_facts.data = data
        return custom_facts

    def __iter__(self):
        return iter(list(self.data.items()))


class CustomFactsFileError(Exception):
    pass


class CustomFactsFile(object):
    def __init__(self, path=None):
        self.path = path
        self.buf = None

    def _open_and_read(self):
        try:
            with open(self.path, 'r') as fd:
                return fd.read()
        except IOError:
            log.warn("Unable to open custom facts file: %s" % self.path)
            raise

    def read(self):
        custom_facts_data = self._open_and_read()
        return custom_facts_data

    def close(self):
        pass


class CustomFactsDirectory(object):
    def __init__(self, path=None, glob_pattern=None):
        self.path = path
        self.glob_pattern = glob_pattern

    def fact_file_path_iterator(self):
        facts_file_glob = os.path.join(self.path, self.glob_pattern)
        return glob.iglob(facts_file_glob)

    def fact_file_iterator(self, fact_file_path_iterator):
        for fact_file_path in fact_file_path_iterator:
            log.debug("Loading custom facts from: %s" % fact_file_path)
            yield CustomFactsFile(fact_file_path)

    def __iter__(self):
        for fact_file in self.fact_file_iterator(self.fact_file_path_iterator()):
            yield CustomFacts.from_json(fact_file.read())


class CustomFactsDirectories(object):
    def __init__(self, path_and_globs):
        self.path_and_globs = path_and_globs

    def __iter__(self):
        for path, glob_pattern in self.path_and_globs:
            yield CustomFactsDirectory(path, glob_pattern)


class CustomFactsCollector(FactsCollector):
    def __init__(self, prefix=None, testing=None, collected_hw_info=None,
                 path_and_globs=None):
        super(CustomFactsCollector, self).__init__(
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )
        self.path_and_globs = path_and_globs
        if path_and_globs is None:
            self.path_and_globs = [
                (os.path.join(rhsm.config.DEFAULT_CONFIG_DIR, 'facts'), '*.facts')
            ]
        self.facts_directories = CustomFactsDirectories(self.path_and_globs)

    def get_all(self):
        facts_dict = {}
        for facts_dir in self.facts_directories:
            for custom_facts in facts_dir:
                facts_dict.update(custom_facts.data)
        return facts_dict
