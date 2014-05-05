

from iniparse import ConfigParser


class RepoFileConfigParser(ConfigParser):
    pass


class RepoFile(object):
    def __init__(self):
        self.config_parser = RepoFileConfigParser()
