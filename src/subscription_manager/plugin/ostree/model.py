
import re

from subscription_manager.plugin.ostree import repo_file

OSTREE_REPO_CONFIG = "/ostree/repo/config"

REMOTE_SECTION_MATCH = """remote\s+["'](.+)['"]"""


class OstreeRemote(object):
    @classmethod
    def from_config_section(cls, section, items):
        remote = cls()
        remote.url = items['url']
        remote.branches = items['branches']
        remote.gpg_verify = items['gpg-verify']
        name = OstreeRemote.name_from_section(section)
        remote.name = name
        return remote

    @staticmethod
    def name_from_section(section):
        """Parse the remote name from the name of the config file section.

        ie, 'remote "awesome-os-7-ostree"' -> "awesome-os-7-ostree".
        """
        matcher = re.compile(REMOTE_SECTION_MATCH)
        result = matcher.match(section)
        if result:
            return result.group(0)

        # FIXME
        raise Exception

    @classmethod
    def from_content(cls, content):
        remote = cls()
        remote.name = content.label
        remote.url = content.url

        # ?


class OstreeRemotes(object):
    def __init__(self):
        # FIXME: are remotes a set or a list?
        self.data = []

    @classmethod
    def from_config(cls, repo_config):
        remotes = cls()
        sections = repo_config.remote_sections()
        for section in sections:
            items = repo_config.items()
            remote = OstreeRemote.from_config_section(section, items)
            remotes.data.append(remote)
        return cls


class OstreeRemoteUpdater(object):
    """Update the config for a ostree repo remote."""
    def __init__(self, report):
        self.report = report

    def update(self, remote):
        # replace old one with new one
        pass


class OstreeRemotesUpdater(object):
    """Update ostree_remotes with new remotes."""
    def __init__(self, ostree_remotes, report=None):
        self.report = report
        self.ostree_remotes = ostree_remotes

    def update(self, remotes_set):
        # Just replaces all of the current remotes with the computed remotes.
        # TODO: if we need to support merging, we can't just replace the set,
        #       Would need to have a merge that updates a OstreeRemote one at a
        #       time.
        # Or a subclass could provide a more detailed update
        self.ostree_remotes = remotes_set

        # TODO: update report


class OstreeRepo(object):
    pass


class OstreeRefspec(object):
    pass


class OstreeOrigin(object):
    pass


# whatever is in config:[core]
class OstreeCore(object):
    pass


class OstreeConfigRepoConfigFileLoader(object):
    repo_config_file = OSTREE_REPO_CONFIG

    def __init__(self, repo_config_file=None):
        if repo_config_file:
            self.repo_config_file = repo_config_file
        self.remotes = None
        self.core = None

    def load(self):
        # raises ConfigParser.Error based exceptions if there is no config or
        # errors reading it.
        # TODO: when/where do we create it the first time?
        self.repo_config = repo_file.RepoFile(self.repo_config_file)
        self.load_remotes()
        self.load_core()

    def load_remotes(self):
        self.remotes = OstreeRemotes.from_config(self.repo_config)

    def load_core(self):
        self.core = OstreeCore()
        self.core.repo_version = self.repo_config.config_parser.get('core', 'repo_version')
        self.core.mode = self.repo_config.config_parser.get('core', 'mode')


class OstreeConfigUpdates(object):
    """The info a ostree update action needs to update OstreeConfig.

    remote sets, origin, refspec, branches, etc.
    """
    def __init__(self, core=None, remote_set=None):
        self.core = core
        self.remote_set = remote_set


class OstreeConfigUpdatesBuilder(object):
    def __init__(self, ostree_config, content_set, report=None):
        self.ostree_config = ostree_config
        self.content_set = content_set
        self.report = report

    def build(self):
        """Figure out what the new config should be, and return a OstreeConfigUpdates."""
        # NOTE: Assume 1 content == 1 remote.
        # If that's not valid, this has to do more.
        remote_set = set()
        for content in self.content_set:
            remote = OstreeRemote.from_content(content)
            remote_set.add(remote)

        updates = OstreeConfigUpdates(self.ostree_config.core,
                                      remote_set=remote_set)
        return updates


class OstreeConfig(object):
    def __init__(self):
        self.remotes = None
        self.core = None

        self.repo_config_loader = OstreeConfigRepoConfigFileLoader()

    def load(self):
        self.repo_config_loader.load()

        self.remotes = self.repo_config_loader.remotes
        self.core = self.repo_config_loader.core


# still needs origin, etc
class OstreeConfigController(object):
    def __init__(self, ostree_config=None, report=None):
        self.ostree_config = ostree_config
        self.report = report

    def update(self, updates):
        remotes_updater = OstreeRemotesUpdater(ostree_remotes=self.ostree_config.remotes,
                                              report=self.report)
        remotes_updater.update(updates.remote_set)

        # update core
        # update origin
