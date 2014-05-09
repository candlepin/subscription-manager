
import logging
import re

from subscription_manager.plugin.ostree import repo_file

OSTREE_REPO_CONFIG = "/ostree/repo/config"

REMOTE_SECTION_MATCH = """remote\s+["'](.+)['"]"""

log = logging.getLogger("rhsm-app." + __name__)


class OstreeRemote(object):
    """Represent a ostree repo remote.

    A repo remote is one of the the '[remote "ostree-awesomeos-8"]' section in
    ostree repo config (/ostree/repo/config by default).
    """
    @classmethod
    def from_config_section(cls, section, items):
        """Create a OstreeRemote object from a repo config section name and map of items.

        'section' is the name of the remote section in the repo config file. For
          ex: 'remote "ostree-awesomeos-8"'
        'items' is a map of items corresponding to config items for 'section'. Extra
          items we don't understand are ignored. Expect at least 'url'.
        """
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
        """Create a OstreeRemote object based on a rhsm.certificate.Content object.

        'content' is a rhsm.certificate.Content, as found in a
          EntitlementCertificate.contents

        This maps:
            Content.label -> OstreeRemote.name
            Content.url -> OstreeRemote.url

        OstreeRemote.branches is always None for now.
        """

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
    """A container/set of OstreeRemote objects.

    Representing OstreeRemote's as found in the repo configs, or
    as created from ent cert Content objects.
    """
    def __init__(self):
        # TODO: are remotes a set or a list? other?
        self.data = set()

    def add(self, ostree_remote):
        self.data.add(ostree_remote)

    # we can iterate over OstreeRemotes
    def __iter__(self):
        return iter(self.data)

    @classmethod
    def from_config(cls, repo_config):
        """Create a OstreeRemotes from a repo_file.RepoFile object."""
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
        for remote in self.data:
            s = s + " %s\n" % repr(remote)
        s = s + "</OstreeRemotes>\n"
        return s


class OstreeRepo(object):
    pass


class OstreeRefspec(object):
    pass


# TODO: Should be a container
class OstreeOrigin(object):
    pass

# whatever is in config:[core]
# TODO: Should probably just be a container of key, value maps
class OstreeCore(object):
    pass


class OstreeConfigRepoConfigFileLoader(object):
    """Load the repo config file and populate a OstreeConfig.

        Could be a classmethod of OstreeConfig.

        This is the assocation between a OstreeConfig and
        the config file(s) that it was read from.
    """
    repo_config_file = OSTREE_REPO_CONFIG

    def __init__(self, repo_config_file=None):
        if repo_config_file:
            self.repo_config_file = repo_config_file
        self.remotes = None
        self.core = None

        # This

    def load(self):
        """Read ostree repo config, and populate it's data."""
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
        """Persist ostree_config to self.repo_config_file."""
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
        """Update the on disk ostree repo config with it's new remotes."""
        # TODO: we need to figure out how to update sections
        #    this only removes all and adds new ones
        for remote in ostree_config.remotes:
            self.repo_config_file.set_remote(remote)

    def update_core(self, ostree_config):
        """Update core section if need be."""
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
        """Figure out what the new config should be and return a OstreeConfigUpdates.

        Currently, this just creates a new OstreeRemotes containing all the remotes
        in self.content_set. It does no filter or mapping.
        """
        # NOTE: Assume 1 content == 1 remote.
        # If that's not valid, this has to do more.
        new_remotes = OstreeRemotes()

        log.debug("builder.build %s" % self.content_set)
        for content in self.content_set:
            # TODO: we may need to keep a map of original config
            #       remotes -> old Content, old Content -> new Content,
            #       and new Content -> new Remotes.
            # This does not create that map yet.
            remote = OstreeRemote.from_content(content)
            new_remotes.add(remote)

        updates = OstreeConfigUpdates(self.ostree_config.core,
                                      remote_set=new_remotes)
        return updates


class OstreeConfig(object):
    """Represents the config state of the systems ostree tool.

    Config file loading and parsing will create one of these and
    populate it with info.

    OstreeConfig saving serializes OstreeConfig state to the
    configuration files.
    """
    def __init__(self):
        self.remotes = None
        self.core = None

        self.repo_config_loader = OstreeConfigRepoConfigFileLoader()

    # Unsure where the code to (de)serialize, and then persist these should
    # live. Here? OstreeConfigController? The Config file classes?
    def load(self):
        """Load a ostree config files and populate OstreeConfig."""
        self.repo_config_loader.load()

        self.remotes = self.repo_config_loader.remotes
        self.core = self.repo_config_loader.core

    def save(self):
        """Persist OstreeConfig state to ostree config files."""
        log.debug("OstreeConfig.save")

        repo_config_file = self.repo_config_loader.repo_config
        repo_config_file_saver = OstreeConfigRepoConfigFileSave(repo_config_file=repo_config_file)
        repo_config_file_saver.save(self)


# still needs origin, etc
class OstreeConfigController(object):
    """Make changes to a OstreeConfig.

    args: 'ostree_config' is a OstreeConfig object
    """
    def __init__(self, ostree_config=None):
        self.ostree_config = ostree_config

    def update(self, updates):
        """Replace the existing config with the OstreeConfigUpdates 'updates'.

        Note: This replaces the whole set. It does not currently
        update remotes one by one. It will not preserve remotes in
        the config file that are not in the content.

        This also currently doesn't update 'core', and likely
        wont.
        """

        # TODO: Instead of the OstreeConfigUpdates, may make more
        #       sense to just keep a old_ostree_config, and the
        #       new_ostree_config, persist the new, and reload?
        self.ostree_config.remotes = updates.remote_set

        log.debug("controller.update after: %s" % self.ostree_config.remotes)

        # TODO: update origin info

    def save(self):
        """Persist self.ostree_config to disk."""
        log.debug("OstreeConfigController.save")
        self.ostree_config.save()
