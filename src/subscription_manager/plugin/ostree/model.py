
import logging
import re

from subscription_manager.plugin.ostree import repo_file

OSTREE_REPO_CONFIG = "/ostree/repo/config"

REMOTE_SECTION_MATCH = """remote\s+["'](.+)['"]"""

log = logging.getLogger("rhsm-app." + __name__)


class OstreeRemote(object):
    @classmethod
    def from_config_section(cls, section, items):
        remote = cls()
        remote.url = items.get('url')
        remote.branches = items.get('branches')
        # note.. gpg-verify->gpg_verify
        remote.gpg_verify = items.get('gpg-verify')
        # we could add the rest of items here if we had just
        # a dict or a set of tuples instead of class...
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
        remote.branches = None
        return remote

    def __repr__(self):
        r = super(OstreeRemote, self).__repr__()
        return "%s name=%s url=%s branches=%s" % (r, self.name, self.url, self.branches)

    # def to_config


class OstreeRemotes(object):
    def __init__(self):
        # FIXME: are remotes a set or a list?
        self.data = set()

    def add(self, ostree_remote):
        self.data.add(ostree_remote)

    def __iter__(self):
        return iter(self.data)

    @classmethod
    def from_config(cls, repo_config):
        remotes = cls()
        sections = repo_config.remote_sections()
        for section in sections:
            item_list = repo_config.config_parser.items(section)
            log.debug("item_list: %s" % item_list)
            items = dict(item_list)
            log.debug("items: %s" % items)
            remote = OstreeRemote.from_config_section(section, items)
            remotes.add(remote)
        return remotes

    def __str__(self):
        s = "\n%s\n" % self.__class__
#        s = s + "%s\n" % self.data
        for remote in self.data:
            s = s + " %s\n" % repr(remote)
        s = s + "</OstreeRemotes>\n"
        return s


# TODO: is this used?
class OstreeRemoteUpdater(object):
    """Update the config for a ostree repo remote."""
    def __init__(self):
        pass

    def update(self, remote):
        # replace old one with new one
        pass


class OstreeRemotesUpdater(object):
    """Update ostree_remotes with new remotes."""
    def __init__(self, ostree_remotes):
        self.ostree_remotes = ostree_remotes

    def update(self, new_remotes):
        # Just replaces all of the current remotes with the computed remotes.
        # TODO: if we need to support merging, we can't just replace the set,
        #       Would need to have a merge that updates a OstreeRemote one at a
        #       time.
        # Or a subclass could provide a more detailed update
        log.debug("OstreeRemotesUpdater before:\n old:%s new:%s" % (self.ostree_remotes, new_remotes))
        self.ostree_remotes = new_remotes
        log.debug("OstreeRemotesUpdater after:\n old:%s new:%s" % (self.ostree_remotes, new_remotes))
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
    """Load the repo config file and populate a OstreeConfig.

        Could be a classmethod of OstreeConfig.
    """
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
        log.debug("%s load_remotes" % __name__)
        self.remotes = OstreeRemotes.from_config(self.repo_config)
        log.debug("load_remotes: %s" % self.remotes)

    def load_core(self):
        self.core = OstreeCore()
        self.core.repo_version = self.repo_config.config_parser.get('core', 'repo_version')
        self.core.mode = self.repo_config.config_parser.get('core', 'mode')


# persist OstreeConfig object to a config file
class OstreeConfigRepoConfigFileSave(object):
    """Populate config file parser with infrom from OstreeConfig and save."""
    def __init__(self, repo_config_file):
        self.repo_config_file = repo_config_file

    def save(self, ostree_config):
        log.debug("ostreeRepoConfigFileLoader.save %s" % ostree_config)

        # TODO: update sections, instead of deleting all and rewriting
        # may mean OstreeConfigUpdates needs to track old remote -> Content ->
        # new remote
        self.repo_config_file.clear_remotes()

        self.update_remotes(ostree_config)
        self.update_core(ostree_config)
        self.repo_config_file.save()

    # serialize OstreeConfig more generally
    def update_remotes(self, ostree_config):
        # TODO: we need to figure out how to update sections
        #    this only removes all and adds new ones
        for remote in ostree_config.remotes:
            self.repo_config_file.set_remote(remote)

    def update_core(self, ostree_config):
        self.repo_config_file.set_core(ostree_config.core)


class OstreeConfigUpdates(object):
    """The info a ostree update action needs to update OstreeConfig.

    remote sets, origin, refspec, branches, etc.
    """
    def __init__(self, core=None, remote_set=None):
        self.core = core
        self.remote_set = remote_set


class OstreeConfigUpdatesBuilder(object):
    def __init__(self, ostree_config, content_set):
        self.ostree_config = ostree_config
        self.content_set = content_set

    def build(self):
        """Figure out what the new config should be, and return a OstreeConfigUpdates."""
        # NOTE: Assume 1 content == 1 remote.
        # If that's not valid, this has to do more.
        new_remotes = OstreeRemotes()
        log.debug("builder.build %s" % self.content_set)
        for content in self.content_set:
            remote = OstreeRemote.from_content(content)
            new_remotes.add(remote)

        log.debug(new_remotes)
        updates = OstreeConfigUpdates(self.ostree_config.core,
                                      remote_set=new_remotes)
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

    def save(self):
        log.debug("OstreeConfig.save")

        repo_config_file = self.repo_config_loader.repo_config
        repo_config_file_saver = OstreeConfigRepoConfigFileSave(repo_config_file=repo_config_file)
        repo_config_file_saver.save(self)


# still needs origin, etc
class OstreeConfigController(object):
    def __init__(self, ostree_config=None):
        self.ostree_config = ostree_config

    def update(self, updates):
        self.ostree_config.remotes = updates.remote_set

        log.debug("controller.update after: %s" % self.ostree_config.remotes)

    def flex_update(self, updates):
        remotes_updater = OstreeRemotesUpdater(ostree_remotes=self.ostree_config.remotes)
        remotes_updater.update(updates.remote_set)
        log.debug("controller.update after: %s" % self.ostree_config.remotes)

    def save(self):
        log.debug("OstreeConfigController.save")
        log.debug("self.ostree_condig.remote_set: %s" % self.ostree_config.remotes)
        self.ostree_config.save()
        # update core
        # update origin
