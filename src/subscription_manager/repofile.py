#
# -*- coding: utf-8 -*-#
from __future__ import print_function, division, absolute_import

# Copyright (c) 2010 Red Hat, Inc.
# Copyright (c) 2017 ATIX AG
#
# Authors: Jeff Ortel <jortel@redhat.com>
#          Matthias Dellweg <dellweg@atix.de>
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

from iniparse import RawConfigParser as ConfigParser
import logging
import os
import re
import string

try:
    from debian.deb822 import Deb822
    HAS_DEB822 = True
except ImportError as e:
    HAS_DEB822 = False

from subscription_manager import utils
from subscription_manager.certdirectory import Path
from six.moves import configparser
from six.moves.urllib.parse import parse_qs, urlparse, urlunparse, urlencode

from rhsm.config import initConfig

from rhsmlib.services import config


log = logging.getLogger(__name__)

conf = config.Config(initConfig())

repo_files = []


class Repo(dict):
    # (name, mutable, default) - The mutability information is only used in disconnected cases
    PROPERTIES = {
            'name': (0, None),
            'baseurl': (0, None),
            'enabled': (1, '1'),
            'gpgcheck': (1, '1'),
            'gpgkey': (0, None),
            'sslverify': (1, '1'),
            'sslcacert': (0, None),
            'sslclientkey': (0, None),
            'sslclientcert': (0, None),
            'metadata_expire': (1, None),
            'enabled_metadata': (1, '0'),
            'proxy': (0, None),
            'proxy_username': (0, None),
            'proxy_password': (0, None),
            'ui_repoid_vars': (0, None)}

    def __init__(self, repo_id, existing_values=None):
        # existing_values is a list of 2-tuples
        existing_values = existing_values or []
        self.id = self._clean_id(repo_id)

        # used to store key order, so we can write things out in the order
        # we read them from the config.
        self._order = []

        self.content_type = None

        for key, value in existing_values:
            # only set keys that have a non-empty value, to not clutter the
            # file.
            if value:
                self[key] = value

        # NOTE: This sets the above properties to the default values even if
        # they are not defined on disk. i.e. these properties will always
        # appear in this dict, but their values may be None.
        for k, (_m, d) in list(self.PROPERTIES.items()):
            if k not in list(self.keys()):
                self[k] = d

    def copy(self):
        new_repo = Repo(self.id)
        for key, value in list(self.items()):
            new_repo[key] = value
        return new_repo

    @classmethod
    def from_ent_cert_content(cls, content, baseurl, ca_cert, release_source):
        """Create an instance of Repo() from an ent_cert.EntitlementCertContent().

        And the other out of band info we need including baseurl, ca_cert, and
        the release version string.
        """
        repo = cls(content.label)

        repo.content_type = content.content_type

        repo['name'] = content.name

        if content.enabled:
            repo['enabled'] = "1"
            repo['enabled_metadata'] = "1"
        else:
            repo['enabled'] = "0"
            repo['enabled_metadata'] = "0"

        expanded_url_path = Repo._expand_releasever(release_source, content.url)
        repo['baseurl'] = utils.url_base_join(baseurl, expanded_url_path)

        # Extract the variables from the url
        repo_parts = repo['baseurl'].split("/")
        repoid_vars = [part[1:] for part in repo_parts if part.startswith("$")]
        if repoid_vars:
            repo['ui_repoid_vars'] = " ".join(repoid_vars)

        # If no GPG key URL is specified, turn gpgcheck off:
        gpg_url = content.gpg
        if not gpg_url:
            gpg_url = ''
            repo['gpgcheck'] = '0'
        else:
            gpg_url = utils.url_base_join(baseurl, gpg_url)
            # Leave gpgcheck as the default of 1
        repomd_gpg_url = conf['rhsm']['repomd_gpg_url']
        if repomd_gpg_url:
            repomd_gpg_url = utils.url_base_join(baseurl, repomd_gpg_url)
            if not gpg_url or gpg_url in ['https://', 'http://']:
                gpg_url = repomd_gpg_url
            elif repomd_gpg_url not in gpg_url:
                gpg_url += ',' + repomd_gpg_url
        repo['gpgkey'] = gpg_url

        repo['sslclientkey'] = content.cert.key_path()
        repo['sslclientcert'] = content.cert.path
        repo['sslcacert'] = ca_cert
        repo['metadata_expire'] = content.metadata_expire

        repo = Repo._set_proxy_info(repo)

        return repo

    @staticmethod
    def _set_proxy_info(repo):
        proxy = ""

        proxy_scheme = conf['server']['proxy_scheme']

        if proxy_scheme.endswith("://"):
            proxy_scheme = proxy_scheme[:-3]

        # Worth passing in proxy config info to from_ent_cert_content()?
        # That would decouple Repo some
        proxy_host = conf['server']['proxy_hostname']

        # proxy_port as string is fine here
        proxy_port = conf['server']['proxy_port']

        if proxy_host != "":
            if proxy_port:
                proxy_host = proxy_host + ":" + proxy_port
            proxy = proxy_scheme + "://" + proxy_host

        # These could be empty string, in which case they will not be
        # set in the yum repo file:
        repo['proxy'] = proxy
        repo['proxy_username'] = conf['server']['proxy_user']
        repo['proxy_password'] = conf['server']['proxy_password']

        return repo

    @staticmethod
    def _expand_releasever(release_source, contenturl):
        # no $releasever to expand
        if release_source.marker not in contenturl:
            return contenturl

        expansion = release_source.get_expansion()

        # NOTE: This is building a url from external info
        #       so likely needs more validation. In our case, the
        #       external source is trusted (release list from tls
        #       mutually authed cdn, or a tls mutual auth api)
        # NOTE: The on disk cache is more vulnerable, since it is
        #       trusted.
        return contenturl.replace(release_source.marker,
                                  expansion)

    def _clean_id(self, repo_id):
        """
        Format the config file id to contain only characters that yum expects
        (we'll just replace 'bad' chars with -)
        """
        new_id = ""
        valid_chars = string.ascii_letters + string.digits + "-_.:"
        for byte in repo_id:
            if byte not in valid_chars:
                new_id += '-'
            else:
                new_id += byte

        return new_id

    def items(self):
        """
        Called when we fetch the items for this yum repo to write to disk.
        """
        # Skip anything set to 'None' or empty string, as this is likely
        # not intended for a yum repo file. None can result here if the
        # default is None, or the entitlement certificate did not have the
        # value set.
        #
        # all values will be in _order, since the key has to have been set
        # to get into our dict.
        return tuple([(k, self[k]) for k in self._order if
                     k in self and self[k]])

    def __setitem__(self, key, value):
        if key not in self._order:
            self._order.append(key)
        dict.__setitem__(self, key, value)

    def __str__(self):
        s = []
        s.append('[%s]' % self.id)
        for k in self.PROPERTIES:
            v = self.get(k)
            if v is None:
                continue
            s.append('%s=%s' % (k, v))

        return '\n'.join(s)

    def __eq__(self, other):
        return (self.id == other.id)

    def __hash__(self):
        return hash(self.id)


def manage_repos_enabled():

    try:
        manage_repos = conf['rhsm'].get_int('manage_repos')
    except ValueError as e:
        log.exception(e)
        return True
    except configparser.Error as e:
        log.exception(e)
        return True
    else:
        if manage_repos is None:
            return True

    return bool(manage_repos)


class TidyWriter(object):

    """
    ini file reader that removes successive newlines,
    and adds a trailing newline to the end of a file.

    used to keep our repo file clean after removals and additions of
    new sections, as iniparser's tidy function is not available in all
    versions.
    """

    def __init__(self, backing_file):
        self.backing_file = backing_file
        self.ends_with_newline = False
        self.writing_empty_lines = False

    def write(self, line):
        lines = line.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line == "":
                if i != len(lines) - 1:
                    if not self.writing_empty_lines:
                        self.backing_file.write("\n")
                    self.writing_empty_lines = True
            else:
                self.writing_empty_lines = False
                self.backing_file.write(line)
                if i != len(lines) - 1:
                    self.backing_file.write("\n")

            i += 1

        if lines[-1] == "":
            self.ends_with_newline = True
        else:
            self.ends_with_newline = False

    def close(self):
        if not self.ends_with_newline:
            self.backing_file.write("\n")


class RepoFileBase(object):

    def __init__(self, path=None, name=None):
        # note PATH get's expanded with chroot info, etc
        path = path or self.PATH
        name = name or self.NAME
        self.path = Path.join(path, name)
        self.repos_dir = Path.abs(path)
        self.manage_repos = manage_repos_enabled()
        # Simulate manage repos turned off if no repos directory exists.
        # This indicates the corresponding package manager is not installed so
        # clearly no need for us to manage repos.
        if not self.path_exists(self.repos_dir):
            log.warn("%s does not exist, turning manage_repos off." %
                    self.repos_dir)
            self.manage_repos = False
        else:
            self.create()

    # Easier than trying to mock/patch os.path.exists
    def path_exists(self, path):
        "wrapper around os.path.exists"
        return os.path.exists(path)

    def exists(self):
        return self.path_exists(self.path)

    def create(self):
        if self.path_exists(self.path) or not self.manage_repos:
            return
        with open(self.path, 'w') as f:
            f.write(self.REPOFILE_HEADER)

    def fix_content(self, content):
        return content

    @classmethod
    def installed(cls):
        return os.path.exists(Path.abs(cls.PATH))

    @classmethod
    def server_value_repo_file(cls):
        return cls('var/lib/rhsm/repo_server_val/')


if HAS_DEB822:
    class AptRepoFile(RepoFileBase):

        PATH = 'etc/apt/sources.list.d'
        NAME = 'rhsm.sources'
        CONTENT_TYPES = ['deb']
        REPOFILE_HEADER = """#
# Certificate-Based Repositories
# Managed by (rhsm) subscription-manager
#
# *** This file is auto-generated.  Changes made here will be over-written. ***
# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***
#
# If this file is empty and this system is subscribed consider
# a "apt-get update" to refresh available repos
#
# *** DO NOT EDIT THIS FILE ***
#
"""

        def __init__(self, path=None, name=None):
            super(AptRepoFile, self).__init__(path, name)
            self.repos822 = []

        def read(self):
            with open(self.path, 'r') as f:
                for repo822 in Deb822.iter_paragraphs(f, shared_storage=False):
                    self.repos822.append(repo822)

        def write(self):
            if not self.manage_repos:
                log.debug("Skipping write due to manage_repos setting: %s" %
                        self.path)
                return
            with open(self.path, 'w') as f:
                f.write(self.REPOFILE_HEADER)
                for repo822 in self.repos822:
                    f.write('\n')
                    repo822.dump(f)

        def add(self, repo):
            repo_dict = dict([(str(k), str(v)) for (k, v) in repo.items()])
            repo_dict['id'] = repo.id
            self.repos822.append(Deb822(repo_dict))

        def delete(self, repo):
            self.repos822[:] = [repo822 for repo822 in self.repos822 if repo822['id'] != repo.id]

        def update(self, repo):
            repo_dict = dict([(str(k), str(v)) for (k, v) in repo.items()])
            repo_dict['id'] = repo.id
            self.repos822[:] = [repo822 if repo822['id'] != repo.id else Deb822(repo_dict) for repo822 in self.repos822]

        def section(self, repo_id):
            result = [repo822 for repo822 in self.repos822 if repo822['id'] == repo_id]
            if len(result) > 0:
                return Repo(result[0]['id'], result[0].items())
            else:
                return None

        def sections(self):
            return [Repo(repo822) for repo822 in self.repos822]

        def fix_content(self, content):
            # Luckily apt ignores all Fields it does not recognize
            baseurl = content['baseurl']
            url_res = re.match(r"^https?://(?P<location>.*)$", baseurl)
            ent_res = re.match(r"^/etc/pki/entitlement/(?P<entitlement>.*).pem$", content['sslclientcert'])
            if url_res and ent_res:
                location = url_res.group('location')
                entitlement = ent_res.group('entitlement')
                baseurl = 'katello://{}@{}'.format(entitlement, location)

            apt_cont = content.copy()
            apt_cont['Types'] = 'deb'
            apt_cont['URIs'] = baseurl
            apt_cont['Suites'] = 'default'
            apt_cont['Components'] = 'all'
            apt_cont['Trusted'] = 'yes'
            return apt_cont


class YumRepoFile(RepoFileBase, ConfigParser):

    PATH = 'etc/yum.repos.d/'
    NAME = 'redhat.repo'
    CONTENT_TYPES = ['yum']
    REPOFILE_HEADER = """#
# Certificate-Based Repositories
# Managed by (rhsm) subscription-manager
#
# *** This file is auto-generated.  Changes made here will be over-written. ***
# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***
#
# If this file is empty and this system is subscribed consider
# a "yum repolist" to refresh available repos
#
"""

    def __init__(self, path=None, name=None):
        ConfigParser.__init__(self)
        RepoFileBase.__init__(self, path, name)

    def read(self):
        ConfigParser.read(self, self.path)

    def _configparsers_equal(self, otherparser):
        if set(otherparser.sections()) != set(self.sections()):
            return False

        for section in self.sections():
            # Sometimes we end up with ints, but values must be strings to compare
            current_items = dict([(str(k), str(v)) for (k, v) in self.items(section)])
            if current_items != dict(otherparser.items(section)):
                return False
        return True

    def _has_changed(self):
        '''
        Check if the version on disk is different from what we have loaded
        '''
        on_disk = ConfigParser()
        on_disk.read(self.path)
        return not self._configparsers_equal(on_disk)

    def write(self):
        if not self.manage_repos:
            log.debug("Skipping write due to manage_repos setting: %s" %
                    self.path)
            return
        if self._has_changed():
            f = open(self.path, 'w')
            tidy_writer = TidyWriter(f)
            ConfigParser.write(self, tidy_writer)
            tidy_writer.close()
            f.close()

    def add(self, repo):
        self.add_section(repo.id)
        self.update(repo)

    def delete(self, section):
        return self.remove_section(section)

    def update(self, repo):
        # Need to clear out the old section to allow unsetting options:
        # don't use remove section though, as that will reorder sections,
        # and move whitespace around (resulting in more and more whitespace
        # as time progresses).
        for (k, v) in self.items(repo.id):
            self.remove_option(repo.id, k)

        for k, v in list(repo.items()):
            ConfigParser.set(self, repo.id, k, v)

    def section(self, section):
        if self.has_section(section):
            return Repo(section, self.items(section))


class ZypperRepoFile(YumRepoFile):

    PATH = 'etc/rhsm/zypper.repos.d'
    NAME = 'redhat.repo'
    REPOFILE_HEADER = """#
# Certificate-Based Repositories
# Managed by (rhsm) subscription-manager
#
# *** This file is auto-generated.  Changes made here will be over-written. ***
# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***
#
# If this file is empty and this system is subscribed consider
# a "zypper lr" to refresh available repos
#
"""

    def __init__(self, path=None, name=None):
        super(ZypperRepoFile, self).__init__(path, name)

    def fix_content(self, content):
        zypper_cont = content.copy()
        sslverify = zypper_cont['sslverify']
        sslcacert = zypper_cont['sslcacert']
        sslclientkey = zypper_cont['sslclientkey']
        sslclientcert = zypper_cont['sslclientcert']
        proxy = zypper_cont['proxy']
        proxy_username = zypper_cont['proxy_username']
        proxy_password = zypper_cont['proxy_password']

        del zypper_cont['sslverify']
        del zypper_cont['sslcacert']
        del zypper_cont['sslclientkey']
        del zypper_cont['sslclientcert']
        del zypper_cont['proxy']
        del zypper_cont['proxy_username']
        del zypper_cont['proxy_password']
        # NOTE looks like metadata_expire and ui_repoid_vars are ignored by zypper

        # clean up data for zypper
        if zypper_cont['gpgkey'] in ['https://', 'http://']:
            del zypper_cont['gpgkey']

        baseurl = zypper_cont['baseurl']
        parsed = urlparse(baseurl)
        zypper_query_args = parse_qs(parsed.query)
        if sslverify and sslverify in ['1']:
            zypper_query_args['ssl_verify'] = 'host'
        if sslcacert:
            zypper_query_args['ssl_capath'] = os.path.dirname(sslcacert)
        if sslclientkey:
            zypper_query_args['ssl_clientkey'] = sslclientkey
        if sslclientcert:
            zypper_query_args['ssl_clientcert'] = sslclientcert
        if proxy:
            zypper_query_args['proxy'] = proxy
        if proxy_username:
            zypper_query_args['proxyuser'] = proxy_username
        if proxy_password:
            zypper_query_args['proxypass'] = proxy_password
        zypper_query = urlencode(zypper_query_args)

        new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, zypper_query, parsed.fragment))
        zypper_cont['baseurl'] = new_url

        return zypper_cont

    # We need to overwrite this, to avoid name clashes with yum's server_val_repo_file
    @classmethod
    def server_value_repo_file(cls):
        return cls('var/lib/rhsm/repo_server_val/', 'zypper_{}'.format(cls.NAME))


def init_repo_file_classes():
    repo_file_classes = [YumRepoFile, ZypperRepoFile]
    if HAS_DEB822:
        repo_file_classes.append(AptRepoFile)
    _repo_files = [
        (RepoFile, RepoFile.server_value_repo_file)
        for RepoFile in repo_file_classes
        if RepoFile.installed()
    ]
    return _repo_files


def get_repo_file_classes():
    global repo_files
    if not repo_files:
        repo_files = init_repo_file_classes()
    return repo_files
