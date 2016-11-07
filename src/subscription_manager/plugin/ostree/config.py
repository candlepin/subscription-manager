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
import os

from rhsm import config
from subscription_manager import utils

# iniparse.utils isn't in old versions
# but it's always there if ostree is
iniparse_tidy = None
try:
    from iniparse.utils import tidy as iniparse_tidy
except ImportError:
    pass

log = logging.getLogger(__name__)

CFG = config.initConfig()

"""Ostree has two config files, both based on the freedesktop.org
Desktop Entry spec. This defines a file format based on "ini" style
config files. Ostree refers to these as "key files".

One config file is the "repo" config, that defines some
core config options, and the ostree "remotes".

The other is an "origin" file that includes a refspec
for a given ostree sha. We no longer check this origin
file. We leave it to the rpm-ostree and ostree tools to deal with.

We base the config parser on rhsm.config.RhsmConfigParser,
except with "defaults" support removed.

We have a KeyFileConfigParser, and one subclass of it
for RepoFileConfigParser.

There is also an OstreeConfigFile, and one subclass of
it for RepoFile. These add some file type
specific helper functions.

RepoFile has a RepoFileConfigParser, but adds methods for
dealing with all of the remote sections.
"""


class RefspecFormatException(Exception):
    """A ostree refspec value was not in the expected format."""
    pass


# KeyFile is the desktop.org name for ini files, more or less
class KeyFileConfigParser(config.RhsmConfigParser):
    """A ini/ConfigParser subclass based on RhsmConfigParser.

    This impl removes the RhsmConfigParser support for rhsm.config.DEFAULTS.
    We don't neeed them.
    """

    # neuter the rhsm.config module level DEFAULTS
    # If we don't override defaults, sections, items, and has_default
    # the class returns the module level DEFAULTS. We don't want that,
    # but we also don't want to monkeypatch our config module.
    #
    # why? useful convience methods on RhsmConfigParser
    # why not pyxdg xdg.IniFile? woudl still have to add type casts
    # why noy pyxdg xdg.DesktopEntry?  the repo configs are not actually
    #    desktop files, just that format, so that class throws exceptions
    #    in that case.
    def defaults(self):
        return {}

    def sections(self):
        # we want to by pass the parent class, and use the base class
        # section, but that's super weird, and it's just this, so c&p. sigh
        return list(self.data)

    def items(self, section):
        result = {}
        if self.has_section(section):
            super_result = super(KeyFileConfigParser, self).options(section)
            for key in super_result:
                result[key] = self.get(section, key)
        return result.items()

    def has_default(self, section, prop):
        return False

    def tidy(self):
        # tidy up config file, rm empty lines, insure newline at eof, etc
        if iniparse_tidy:
            iniparse_tidy(self)

    def save(self, config_file=None):
        self.tidy()

        # create /ostree/repo/config if /ostree/repo exists
        dir_name = os.path.dirname(self.config_file)
        if not os.path.exists(dir_name):
            log.warn("%s does not exist, so unable to save %s",
                     dir_name, self.config_file)
            return

        super(KeyFileConfigParser, self).save()


class BaseOstreeConfigFile(object):
    config_parser_class = KeyFileConfigParser

    def __init__(self, filename=None):
        self.filename = filename
        self.config_parser = self._get_config_parser()

    def _get_config_parser(self):
        return self.config_parser_class(config_file=self.filename)

    def save(self):
        self.config_parser.save()


class RepoFile(BaseOstreeConfigFile):
    """Ostree repo config file specific OstreeConfigFile implementation.

    Knows how to get the list of 'remote' sections, and how to determine
    if a config parser section is a remote.
    """
    config_parser_class = KeyFileConfigParser

    def remote_sections(self):
        """Return all the config sections for "remotes".

        Note: this returns a list of section name strings, not
              OstreeRemotes
        """
        # flatten to comprehension
        remotes = []
        for section in self.config_parser.sections():
            if self.section_is_remote(section):
                remotes.append(section)
        return remotes

    def section_is_remote(self, section):
        """Determine if a config section represents a ostree remote.

        For example, the section named 'remote "awesomeos-ostree-1"' is a remote.
        """
        if section.startswith("remote"):
            return True

    def clear_remotes(self):
        """Remove all the config sections for remotes."""

        for remote in self.remote_sections():
            # do we need to delete options and section or just section?
            for key, value in self.config_parser.items(remote):
                self.config_parser.remove_option(remote, key)
            self.config_parser.remove_section(remote)

    def set(self, section, key, value):
        return self.config_parser.set(section, key, value)

    def get_proxy(self):
        proxy_host = CFG.get('server', 'proxy_hostname')
        # proxy_port as string is fine here
        proxy_port = CFG.get('server', 'proxy_port')
        proxy_user = CFG.get('server', 'proxy_user')
        proxy_password = CFG.get('server', 'proxy_password')

        proxy_uri = None
        if proxy_host == "":
            return proxy_uri

        proxy_auth = ""
        if proxy_user != "" and proxy_password != "":
            proxy_auth = "%s:%s@" % (proxy_user, proxy_password)

        # TODO: does libsoup want all proxies to be 'http'
        proxy_uri = "http://%s%s" % (proxy_auth, proxy_host)

        if proxy_port != "":
            proxy_uri = "%s:%s" % (proxy_uri, proxy_port)

        return proxy_uri
        # These could be empty string, in which case they will not be
        # set in the yum repo file:

    def set_remote(self, ostree_remote):
        """Add a remote section to config file based on a OstreeRemote."""
        # format section name
        section_name = 'remote ' + '"%s"' % ostree_remote.name

        # Assume all remotes will share the same cdn
        # This is really info about a particular CDN, we just happen
        # to only support one at the moment.
        baseurl = CFG.get('rhsm', 'baseurl')
        ca_cert = CFG.get('rhsm', 'repo_ca_cert')

        full_url = utils.url_base_join(baseurl, ostree_remote.url)

        self.set(section_name, 'url', full_url)

        # gpg_verify not set
        gpg_verify_string = 'true' if ostree_remote.gpg_verify else 'false'
        self.set(section_name, 'gpg-verify', gpg_verify_string)

        if ostree_remote.tls_client_cert_path:
            self.set(section_name, 'tls-client-cert-path', ostree_remote.tls_client_cert_path)
        if ostree_remote.tls_client_key_path:
            self.set(section_name, 'tls-client-key-path', ostree_remote.tls_client_key_path)

        # Ideally, setting the tls-ca-path would be depending on the
        # baseurl and/or the CDN and if the content uses https. We always
        # use https though, and the content does not know the CDN it comes
        # from. Need a way to map a Content to a particular CDNInfo, and to
        # support multiple CDNInfos setup.
        self.set(section_name, 'tls-ca-path', ca_cert)

        proxy_uri = self.get_proxy()
        if proxy_uri:
            self.set(section_name, 'proxy', proxy_uri)

    def set_core(self, ostree_core):
        # Assuming we don't need to check validy of any [core] values
        # update the core section with the current values
        for key in ostree_core:
            self.set('core', key, ostree_core.get(key))

    def get_core(self):
        return self.config_parser.items('core')
