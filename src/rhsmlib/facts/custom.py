import glob
import logging

from rhsm import ourjson
from rhsmlib.facts.collector import FactsCollector

log = logging.getLogger(__name__)


class CustomFacts(object):
    def __init__(self, data=None):
        self.data = data

    @classmethod
    def from_json(cls, json_blob):
        custom_facts = cls

        try:
            data = ourjson.loads(json_blob)
        except ValueError:
            log.warn("Unable to load custom facts file.")

        custom_facts.data = data
        return custom_facts

    def __iter__(self):
        return iter(self.data.items())


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
        facts_file_glob = "%s/%s" % (self.path, self.glob_pattern)
        return glob.iglob(facts_file_glob)

    def fact_file_iterator(self, fact_file_path_iterator):
        for fact_file_path in fact_file_path_iterator:
            log.info("Loading custom facts from: %s" % fact_file_path)
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
        super(CustomFactsCollector, self).__init__(prefix=prefix,
                                                   testing=testing,
                                                   collected_hw_info=collected_hw_info)
        self.path_and_globs = path_and_globs
        self.facts_directories = CustomFactsDirectories(self.path_and_globs)

    def get_all(self):
        facts_dict = {}
        for facts_dir in self.facts_directories:
            for custom_facts in facts_dir:
                facts_dict.update(custom_facts.data)
        return facts_dict
