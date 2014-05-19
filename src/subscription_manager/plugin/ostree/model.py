#
# Copyright (c) 2014 Red Hat, Inc.
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

import logging
import re
import os
import subprocess
import sys

from subscription_manager.plugin.ostree import config

OSTREE_REPO_CONFIG_PATH = "/ostree/repo/config"

REMOTE_SECTION_MATCH = r"remote\s+\"(?P<remote_name>.+)\""

log = logging.getLogger("rhsm-app." + __name__)


class OstreeContentError(Exception):
    pass


class RemoteSectionNameParseError(OstreeContentError):
    pass


# FIXME: remove property stuff, dont inherit from dict, remove hash stuff
#        it's clever but weird and unneeded, but commit so tests work
class OstreeRemote(object):
    """Represent a ostree repo remote.

    A repo remote is one of the the '[remote "ostree-awesomeos-8"]' section in
    ostree repo config (/ostree/repo/config by default).
    """

    items_to_data = {'gpg-verify': 'gpg_verify'}

    def __init__(self):
        self.data = {}

    # for remote_key in remote iterates over the config items
    def __iter__(self):
        return iter(self.data)

    @property
    def url(self):
        return self.data.get('url')

    @url.setter
    def url(self, value):
        self.data['url'] = value

    @property
    def gpg_verify(self):
        return self.data.get('gpg_verify')

    @gpg_verify.setter
    def gpg_verify(self, value):
        self.data['gpg_verify'] = value

    @property
    def name(self):
        return self.data.get('name')

    @name.setter
    def name(self, value):
        self.data['name'] = value

    @classmethod
    def from_config_section(cls, section, items):
        """Create a OstreeRemote object from a repo config section name and map of items.

        'section' is the name of the remote section in the repo config file. For
          ex: 'remote "ostree-awesomeos-8"'
        'items' is a map of items corresponding to config items for 'section'. Extra
          items we don't understand are ignored. Expect at least 'url'.

        Note: 'gpg-verify' is one of the default items, but 'gpg-verify' is not
              a valid python attribute name, so a key of 'gpg-verify' is used to
              update the OstreeRemote.gpg_verify property.
        """
        remote = cls()

        # transmogrify names
        log.debug("ITEMS: %s" % items)
        for key in items:
            # replace key name with mapping name, defaulting to key name
            remote.data[cls.items_to_data.get(key, key)] = items[key]

        # the section name takes precendence over a 'name' in the items
        remote.name = OstreeRemote.name_from_section(section)
        return remote

    @staticmethod
    def name_from_section(section):
        """Parse the remote name from the name of the config file section.

        ie, 'remote "awesome-os-7-ostree"' -> "awesome-os-7-ostree".
        """
        matcher = re.compile(REMOTE_SECTION_MATCH)
        result = matcher.match(section)
        log.debug("result %s" % result)
        if result:
            return result.groupdict()['remote_name']

        # FIXME
        raise RemoteSectionNameParseError

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

        # TODO: logic for mapping content gpgkey settings to gpg_verify

        remote.gpg_verify = remote.map_gpg(content)

        return remote

    @staticmethod
    def map_gpg(content):
        gpg_verify = False
        if content.gpg:
            gpg_verify = True

        return gpg_verify

    def __repr__(self):
        r = super(OstreeRemote, self).__repr__()
        return '<%s name=%s url=%s gpg_verify=%s>' % (r, self.name, self.url, self.gpg_verify)

    def report(self):
        self.report_template = """remote \"{self.name}\"
    url: {self.url}
    gpg-verify: {self.gpg_verify}"""
        return self.report_template.format(self=self)


class OstreeRemotes(object):
    """A container/set of OstreeRemote objects.

    Representing OstreeRemote's as found in the repo configs, or
    as created from ent cert Content objects.
    """
    def __init__(self):
        self.data = []

    def add(self, ostree_remote):
        self.data.append(ostree_remote)

    # we can iterate over OstreeRemotes
    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    @classmethod
    def from_config(cls, repo_config):
        """Create a OstreeRemotes from a repo_file.RepoFile object."""
        remotes = cls()
        sections = repo_config.remote_sections()
        for section in sections:
            log.debug("section: |%s|" % section)
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


class OstreeConfigRepoFileStore(object):
    """For loading/saving a ostree repo config file."""
    default_repo_file_path = OSTREE_REPO_CONFIG_PATH

    def __init__(self, repo_file_path=None):
        self.repo_file_path = repo_file_path or self.default_repo_file_path
        self.repo_file = None

    def load(self):
        self.repo_file = config.RepoFile(self.repo_file_path)
        return self.repo_file

    def save(self, ostree_config):
        if not self.repo_file:
            self.repo_file = config.RepoFile(self.repo_file_path)

        writer = OstreeConfigRepoFileWriter(self.repo_file)
        writer.save(ostree_config)


# persist OstreeConfig object to a config file
class OstreeConfigRepoFileWriter(object):
    """Populate config file parser with infrom from OstreeConfig and save."""
    def __init__(self, repo_file):
        self.repo_file = repo_file

    def save(self, ostree_config):
        """Persist ostree_config to self.repo_config_file."""
        log.debug("ostreeRepoConfigFileLoader.save %s" % ostree_config)

        # TODO: update sections, instead of deleting all and rewriting
        # may mean OstreeConfigUpdates needs to track old remote -> Content ->
        # new remote
        self.repo_file.clear_remotes()

        self.update_remotes(ostree_config)
        self.update_core(ostree_config)
        self.repo_file.save()

    # serialize OstreeConfig more generally
    def update_remotes(self, ostree_config):
        """Update the OstreeConfig ostree_config's config file with it's new remotes."""
        # TODO: we need to figure out how to update sections
        #    this only removes all and adds new ones
        for remote in ostree_config.remotes:
            self.repo_file.set_remote(remote)

    def update_core(self, ostree_config):
        """Update core section in OstreeConfig ostree_config's config file if need be."""
        self.repo_file.set_core(ostree_config.core)


class OstreeOriginUpdater(object):
    """
    Determines the currently deployed osname and SHA256.origin file,
    and update the remote name to point to what is subscribed.

    In the event that our repo config carries multiple remote names,
    we currently select the first.
    """
    # TODO: solidify what should happen if there are multiple repos in config.
    def __init__(self, repo_config):
        # Already updated repo_config:
        self.repo_config = repo_config

    def _get_deployed_origin(self):
        """
        Get path to the currently deployed origin file.
        """
        # Can't load gobject3 introspection code as we use gobject2 in a couple
        # places. Shell out to a separate script, assumed to be in same location
        # as this module. Let the CalledProcessError bubble up.
        try:
            output = subprocess.check_output([os.path.join(__file__, "gi.py"),
                '--deployed-origin'])
            output = output.strip()
        except subprocess.CalledProcessError, e:
            # Is this an OSTree system? Does it have pygobject3?
            log.error("Error looking up OSTree origin file.")
            log.error(e.output)
            raise e

    def run(self):
        """
        Locate and update the currently deployed origin file.
        """


        # FIXME: return early till we figure out gi/gobject conflicts
        return


        self.originfile = self._get_deployed_origin()
        log.debug("Loading ostree origin file: %s" % self.originfile)
        origin_cfg = config.OriginFileConfigParser(self.originfile)
        old_refspec = origin_cfg.get('origin', 'refspec')

        # TODO: If our repo config has multiple remotes in it, which should we use?
        # For now we are just using a random one from the set:
        if len(self.repo_config.remotes):
            log.warn("Multiple remotes configured in %s." % self.repo_config)

        new_remote = self.repo_config.remotes[0].name
        new_refspec = config.replace_refspec_remote(old_refspec,
            new_remote)

        if new_refspec != old_refspec:
            log.info("Updating refspec in: %s" % self.originfile)
            log.info("    old = %s" % old_refspec)
            log.info("    new = %s" % new_refspec)
            origin_cfg.set('origin', 'refspec', new_refspec)
            origin_cfg.save()
        else:
            log.debug("No change to refspec in %s" % self.originfile)


class OstreeConfigUpdatesBuilder(object):
    def __init__(self, ostree_config, contents):
        self.orig_ostree_config = ostree_config
        self.contents = contents

    def build(self):
        """Figure out what the new config should be and return a OstreeConfigUpdates.

        Currently, this just creates a new OstreeRemotes containing all the remotes
        in self.contents. It does no filter or mapping.
        """
        # NOTE: Assume 1 content == 1 remote.
        # If that's not valid, this has to do more.
        new_remotes = OstreeRemotes()

        content_to_remote = {}
        log.debug("builder.build %s" % self.contents)
        for content in self.contents:
            # TODO: we may need to keep a map of original config
            #       remotes -> old Content, old Content -> new Content,
            #       and new Content -> new Remotes.
            #       This does not create that map yet.
            remote = OstreeRemote.from_content(content)
            new_remotes.add(remote)

            # track for reports
            # mutliple contents to the same remote?
            content_to_remote[content] = remote

        # Use the same 'core' values, but with the new remotes
        new_ostree_config = OstreeConfig(core=self.orig_ostree_config.core,
                                         remotes=new_remotes)

        ostree_config_updates = OstreeConfigUpdates(self.orig_ostree_config, new_ostree_config)
        ostree_config_updates.content_to_remote = content_to_remote

        return ostree_config_updates

# Classes represent ostree configuration objects


class OstreeRepo(object):
    pass


class OstreeCore(dict):
    """Represents the info from the ostree repo config [core] section."""
    pass


class OstreeConfig(object):
    """Represents the config state of the systems ostree tool.

    Config file loading and parsing will create one of these and
    populate it with info.

    OstreeConfig saving serializes OstreeConfig state to the
    configuration files.
    """

    def __init__(self, core=None, remotes=None, repo_file_path=None):
        self.remotes = remotes or OstreeRemotes()
        self.core = core or OstreeCore()
        self.repo_file_path = repo_file_path

        # Wait for load() to load repo file since we
        # create these without a backing store as well.
        self.repo_file_store = None

    def _init_store(self):
        return OstreeConfigRepoFileStore(self.repo_file_path)

    # TODO: Should this be a part of the constructor?
    def load(self):
        """Load a ostree config files and populate OstreeConfig."""
        self.repo_file_store = self._init_store()

        self.repo_file = self.repo_file_store.load()
        self.load_remotes()
        self.load_core()

    def load_remotes(self):
        self.remotes = OstreeRemotes.from_config(self.repo_file)

    def load_core(self):
        self.core = OstreeCore(self.repo_file.get_core())

    def save(self):
        """Persist OstreeConfig state to ostree config files."""
        log.debug("OstreeConfig.save")

        # if we don't have a backing store, open the config fil
        # path at self.repo_file_path
        # and use for backing store
        if not self.repo_file_store:
            self.repo_file_store = self._init_store()

        self.repo_file_store.save(self)

    def __repr__(self):
        s = []
        s.append("<OsTreeConfig repo_file_path=%s>" % self.repo_file_path)
        s.append("Core: %s" % self.core)
        s.append("Remotes: %s" % self.remotes)
        return '\n'.join(s)


class OstreeConfigUpdates(object):
    """The info a ostree update action needs to update OstreeConfig.

    remote sets, origin, refspec, branches, etc.

    Try to keep track of any X->Y changes for reporting.
    """
    def __init__(self, orig, new):
        self.orig = orig
        self.new = new
        self.content_to_remote = {}

    def apply(self):
        self.orig = self.new

    def save(self):
        """Persist self.ostree_config to disk."""
        log.debug("OstreeConfigUpdates.save")
        self.orig.save()
