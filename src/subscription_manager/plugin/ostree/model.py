from __future__ import print_function, division, absolute_import

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

from subscription_manager.plugin.ostree import config

OSTREE_REPO_CONFIG_PATH = "/etc/ostree/remotes.d/redhat.conf"
OSTREE_CORE_CONFIG_PATH = "/ostree/repo/config"

REMOTE_SECTION_MATCH = r"remote\s+\"(?P<remote_name>.+)\""

OSTREE_REPORT_TEMPLATE = """remote \"{self.name}\"
\turl: {self.url}
\tgpg-verify: {self.gpg_verify}
\ttls-client-cert-path: {self.tls_client_cert_path}
\ttls-client-key-path: {self.tls_client_key_path}
\ttls-ca-path: {self.tls_ca_path}"""

log = logging.getLogger(__name__)


class OstreeContentError(Exception):
    pass


class RemoteSectionNameParseError(OstreeContentError):
    def __init__(self, msg=None, section=None):
        self.msg = msg
        self.section = section


class OstreeRemote(object):
    """Represent a ostree repo remote.

    A repo remote is one of the the '[remote "ostree-awesomeos-8"]' section in
    ostree repo config (/ostree/repo/config by default).
    """

    items_to_data = {'gpg-verify': 'gpg_verify',
                     'tls-client-cert-path': 'tls_client_cert_path',
                     'tls-client-key-path': 'tls_client_key_path',
                     'tls-ca-path': 'tls_ca_path'}

    report_template = OSTREE_REPORT_TEMPLATE

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
        return self.data.get('gpg_verify', True)

    @gpg_verify.setter
    def gpg_verify(self, value):
        self.data['gpg_verify'] = value

    @property
    def name(self):
        return self.data.get('name')

    @name.setter
    def name(self, value):
        self.data['name'] = value

    @property
    def tls_client_cert_path(self):
        return self.data.get('tls_client_cert_path')

    @tls_client_cert_path.setter
    def tls_client_cert_path(self, value):
        self.data['tls_client_cert_path'] = value

    @property
    def tls_client_key_path(self):
        return self.data.get('tls_client_key_path')

    @tls_client_key_path.setter
    def tls_client_key_path(self, value):
        self.data['tls_client_key_path'] = value

    @property
    def tls_ca_path(self):
        return self.data.get('tls_ca_path')

    @tls_ca_path.setter
    def tls_ca_path(self, value):
        self.data['tls_ca_path'] = value

    @property
    def proxy(self):
        return self.data.get('proxy')

    @proxy.setter
    def proxy(self, value):
        self.data['proxy'] = value

    @classmethod
    def from_config_section(cls, section, items):
        """Create a OstreeRemote object from a repo config section name and
        map of items.

        'section' is the name of the remote section in the repo config file. For
          ex: 'remote "ostree-awesomeos-8"'
        'items' is a map of items corresponding to config items for
        'section'. Extra
          items we don't understand are ignored. Expect at least 'url'.

        Note: 'gpg-verify' is one of the default items, but 'gpg-verify' is not
              a valid python attribute name, so a key of 'gpg-verify' is used to
              update the OstreeRemote.gpg_verify property.
        """
        remote = cls()

        # transmogrify names
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
        if result:
            return result.groupdict()['remote_name']

        raise RemoteSectionNameParseError(
            "Unable to find a name in section %s" % section,
            section=section)

    @classmethod
    def from_ent_cert_content(cls, content):
        """Create a OstreeRemote object based on a model.Content object.

        This maps:
            Content.label -> OstreeRemote.name
            Content.url -> OstreeRemote.url

        OstreeRemote.branches is always None for now.
        """

        remote = cls()
        remote.name = content.label
        remote.url = content.url

        remote.gpg_verify = remote.map_gpg(content)

        cert = content.cert
        remote.tls_client_cert_path = cert.path
        remote.tls_client_key_path = cert.key_path()

        # NOTE: The tls-ca-path info is not in the Content,
        #       but local system configuration.

        return remote

    @staticmethod
    def map_gpg(content):
        """Map the content.gpg attribute value to True/False/

        Content.gpg is meant for a URL, and is being overloaded
        here for enabled/disabled. Content's representing content
        that is not associated with a gpg key have their 'gpg'
        attribute ('gpg_url' in the json in an ent cert)
        set to "http://". So consider that value also equilivent
        to gpg-verify=false. That is the only value that will
        disable gpg-verify.

        If there are any errors reading/understand the
        Content.gpg, assume gpg_verify = True
        """
        gpg_verify = True

        # No content.gpg means gpg-verify=true as well.
        # This reinforces "no explicit Content.gpg"
        # means to default to gpg_verify=True
        if not hasattr(content, 'gpg'):
            return gpg_verify

        if content.gpg == "http://":
            gpg_verify = False

        # If we need some other sentinal to indicate gpg-verify=false,
        # look for it here.

        return gpg_verify

    def __repr__(self):
        r = super(OstreeRemote, self).__repr__()
        template = "%s\n (name=%s\n url=%s\n gpg_verify=%s\n " \
                   "tls_client_cert_path=%s\n tls_client_key_path=%s\n " \
                   "proxy=%s)"
        return template % (r, self.name, self.url, self.gpg_verify,
                           self.tls_client_cert_path, self.tls_client_key_path,
                           self.proxy)

    def report(self):
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
            item_list = repo_config.config_parser.items(section)
            items = dict(item_list)
            remote = OstreeRemote.from_config_section(section, items)
            remotes.add(remote)
        return remotes

    def __str__(self):
        s = "\n%s\n" % self.__class__
        for remote in self.data:
            s = s + " %s\n" % repr(remote)
        s = s + "</OstreeRemotes>\n"
        return s


class OstreeConfigFileStore(object):
    """For loading/saving a ostree remotes repo config file."""
    default_repo_file_path = OSTREE_REPO_CONFIG_PATH

    def __init__(self, config_file_path=None):
        self.config_file_path = config_file_path or \
            self.default_config_file_path
        self.config_file = None

    def load(self):
        self.config_file = config.RepoFile(self.config_file_path)
        return self.config_file

    def save(self, ostree_config):
        if not self.config_file:
            self.config_file = config.RepoFile(self.config_file_path)

        writer = OstreeConfigFileWriter(self.config_file)
        writer.save(ostree_config)


# persist OstreeConfig object to a config file
class OstreeConfigFileWriter(object):
    """Populate config file parser with infrom from OstreeConfig and save."""

    def __init__(self, repo_file):
        self.repo_file = repo_file

    def save(self, ostree_config):
        """Persist ostree_config to self.repo_config_file."""

        # TODO: update sections, instead of deleting all and rewriting
        # may mean OstreeConfigUpdates needs to track old remote -> Content ->
        # new remote
        self.repo_file.clear_remotes()

        self.update_remotes(ostree_config)
        self.update_core(ostree_config)
        self.repo_file.save()

    # serialize OstreeConfig more generally
    def update_remotes(self, ostree_config):
        """Update the OstreeConfig ostree_config's config file with it's new
        remotes."""
        # TODO: we need to figure out how to update sections
        #    this only removes all and adds new ones
        for remote in ostree_config.remotes:
            self.repo_file.set_remote(remote)

    def update_core(self, ostree_config):
        """Update core section in OstreeConfig ostree_config's config file if
        need be."""
        self.repo_file.set_core(ostree_config.core)


class OstreeConfigUpdatesBuilder(object):
    def __init__(self, ostree_config, contents):
        self.orig_ostree_config = ostree_config
        self.contents = contents

    def build(self):
        """Figure out what the new config should be and return a
        OstreeConfigUpdates.

        Currently, this just creates a new OstreeRemotes containing all the
        remotes in self.contents. It does no filter or mapping.
        """
        # NOTE: Assume 1 content == 1 remote.
        # If that's not valid, this has to do more.
        new_remotes = OstreeRemotes()

        content_to_remote = {}
        for content in self.contents:
            remote = OstreeRemote.from_ent_cert_content(content)
            new_remotes.add(remote)

            # track for reports
            # mutliple contents to the same remote?
            content_to_remote[content] = remote

        new_ostree_config = OstreeConfig(core=self.orig_ostree_config.core,
                                         remotes=new_remotes,
                                         repo_file_path=self.orig_ostree_config.repo_file_path)

        ostree_config_updates = OstreeConfigUpdates(self.orig_ostree_config,
                                                    new_ostree_config)
        ostree_config_updates.content_to_remote = content_to_remote

        return ostree_config_updates


# Classes represent ostree configuration objects


class OstreeCore(dict):
    """Represents the info from the ostree repo config [core] section."""
    pass


class OstreeConfig(object):
    """Represents the config state of the systems ostree tool.

    Config file loading and parsing will create one of these and populate it
    with info.

    OstreeConfig saving serializes OstreeConfig state to the configuration
    files.
    """
    default_repo_file_path = None

    def __init__(self, core=None, remotes=None, repo_file_path=None):
        self.remotes = remotes or OstreeRemotes()
        self.core = core or OstreeCore()
        self.repo_file_path = repo_file_path or self.default_repo_file_path

        # Wait for load() to load repo file since we
        # create these without a backing store as well.
        self.repo_file_store = None

    def _init_store(self):
        return OstreeConfigFileStore(self.repo_file_path)

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

        # if we don't have a backing store, open the config fil
        # path at self.repo_file_path
        # and use for backing store
        if not self.repo_file_store:
            self.repo_file_store = self._init_store()

        self.repo_file_store.save(self)

    def __repr__(self):
        s = []
        r = super(OstreeConfig, self).__repr__()
        s.append("<%s repo_file_path=%s>" % (r, self.repo_file_path))
        s.append("Core: %s" % self.core)
        s.append("Remotes: %s" % self.remotes)
        return '\n'.join(s)


class OstreeCoreConfig(OstreeConfig):
    default_repo_file_path = OSTREE_CORE_CONFIG_PATH


class OstreeRepoConfig(OstreeConfig):
    default_repo_file_path = OSTREE_REPO_CONFIG_PATH


class OstreeConfigUpdates(object):
    """The info a ostree update action needs to update OstreeConfig.

    remote sets, branches, etc.

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
        self.orig.save()
