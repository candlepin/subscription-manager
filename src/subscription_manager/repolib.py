#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

from iniparse import ConfigParser
import logging
import os
import string
import subscription_manager.injection as inj
from subscription_manager.cache import OverrideStatusCache
from urllib import basejoin

from rhsm.config import initConfig
from rhsm.connection import RemoteServerException, RestlibException
from rhsm.utils import UnsupportedOperationException


from certlib import ActionLock, ActionReport, DataLib
from certdirectory import Path, ProductDirectory, EntitlementDirectory

log = logging.getLogger('rhsm-app.' + __name__)

CFG = initConfig()

ALLOWED_CONTENT_TYPES = ["yum"]


class RepoLib(DataLib):

    def __init__(self, lock=ActionLock(), uep=None, cache_only=False):
        self.cache_only = cache_only
        DataLib.__init__(self, lock, uep)
        self.identity = identity or inj.require(inj.IDENTITY)

    def _do_update(self):
        action = RepoUpdateAction(uep=self.uep, cache_only=self.cache_only)
        return action.perform()

    def is_managed(self, repo):
        action = RepoUpdateAction(uep=self.uep, cache_only=self.cache_only)
        return repo in [c.label for c in action.matching_content()]
    def get_repos(self, apply_overrides=True):
        action = RepoUpdateAction(uep=self.uep,
							      cache_only=self.cache_only,
							      apply_overrides=apply_overrides)
        repos = action.get_unique_content()
        if self.identity.is_valid() and action.override_supported:
            return repos

        # Otherwise we are in a disconnected case or dealing with an old server
        current = set()
        # Add the current repo data
        repo_file = RepoFile()
        repo_file.read()
        for repo in repos:
            existing = repo_file.section(repo.id)
            if existing is None:
                current.add(repo)
            else:
                action.update_repo(existing, repo)
                current.add(existing)

        return current

    def get_repo_file(self):
        repo_file = RepoFile()
        return repo_file.path

    @classmethod
    def delete_repo_file(cls):
        repo_file = RepoFile()
        if os.path.exists(repo_file.path):
            os.unlink(repo_file.path)


# WARNING: exact same name as another action in factlib and certlib.
# TODO: This is the third disjoint "Action" class hierarchy, this one inherits nothing
# but exposes similar methods, all of which are already abstracted behind the
# Datalib.update() method anyhow. Pretty sure these can go away.
class RepoUpdateAction:

    def __init__(self, uep, ent_dir=None, prod_dir=None, cache_only=False, apply_overrides=True):
        self.identity = inj.require(inj.IDENTITY)
        if ent_dir:
            self.ent_dir = ent_dir
        else:
            self.ent_dir = EntitlementDirectory()

        if prod_dir:
            self.prod_dir = prod_dir
        else:
            self.prod_dir = ProductDirectory()

        self.uep = uep
        self.manage_repos = 1
        self.apply_overrides = apply_overrides
        if CFG.has_option('rhsm', 'manage_repos'):
            self.manage_repos = int(CFG.get('rhsm', 'manage_repos'))

        self.release = None
        self.overrides = []
        self.override_supported = bool(self.uep and self.uep.supports_resource('content_overrides'))

        # FIXME: empty report at the moment, should be changed to include
        # info about updated repos
        self.report = ActionReport()
        # If we are not registered, skip trying to refresh the
        # data from the server
        if not self.identity.is_valid():
            return

        # Only attempt to update the overrides if they are supported
        # by the server.
        if self.override_supported:
            try:
                override_cache = inj.require(inj.OVERRIDE_STATUS_CACHE)
            except KeyError:
                override_cache = OverrideStatusCache()
            if cache_only:
                status = override_cache._read_cache()
            else:
                status = override_cache.load_status(self.uep, self.identity.uuid)

            if status is not None:
                self.overrides = status

        message = "Release API is not supported by the server. Using default."
        try:
            result = self.uep.getRelease(self.identity.uuid)
            self.release = result['releaseVer']
        except RemoteServerException, e:
            log.debug(message)
        except RestlibException, e:
            if e.code == 404:
                log.debug(message)
            else:
                raise

    def perform(self):
        # Load the RepoFile from disk, this contains all our managed yum repo sections:
        repo_file = RepoFile()

        # the [rhsm] manage_repos can be overridden to disable generation of the
        # redhat.repo file:
        if not self.manage_repos:
            log.debug("manage_repos is 0, skipping generation of: %s" %
                    repo_file.path)
            if repo_file.exists():
                log.info("Removing %s due to manage_repos configuration." %
                        repo_file.path)
                RepoLib.delete_repo_file()
            return 0

        repo_file.read()
        valid = set()
        updates = 0

        # Iterate content from entitlement certs, and create/delete each section
        # in the RepoFile as appropriate:
        for cont in self.get_unique_content():
            valid.add(cont.id)
            existing = repo_file.section(cont.id)
            if existing is None:
                repo_file.add(cont)
                updates += 1
            else:
                # In the non-disconnected case, destroy the old repo and replace it with
                # what's in the entitlement cert plus any overrides.
                if self.identity.is_valid() and self.override_supported:
                    repo_file.update(cont)
                    updates += 1
                else:
                    updates += self.update_repo(existing, cont)
                    repo_file.update(existing)

        for section in repo_file.sections():
            if section not in valid:
                updates += 1
                repo_file.delete(section)

        # Write new RepoFile to disk:
        repo_file.write()
        log.info("repos updated: %s" % updates)
        return updates

    def get_unique_content(self):
        unique = set()
        if not self.manage_repos:
            return unique
        ent_certs = self.ent_dir.list_valid()
        baseurl = CFG.get('rhsm', 'baseurl')
        ca_cert = CFG.get('rhsm', 'repo_ca_cert')
        for ent_cert in ent_certs:
            for r in self.get_content(ent_cert, baseurl, ca_cert):
                unique.add(r)
        return unique

    def get_key_path(self, ent_cert):
        """
        Returns the full path to the cert's key.pem.
        """
        dir_path, cert_filename = os.path.split(ent_cert.path)
        key_filename = "%s-key.%s" % tuple(cert_filename.split("."))
        key_path = os.path.join(dir_path, key_filename)
        return key_path

    def matching_content(self, ent_cert=None):
        if ent_cert:
            certs = [ent_cert]
        else:
            certs = self.ent_dir.list_valid()


        lst = set()


        for cert in certs:
            if not cert.content:
                continue

            tags_we_have = self.prod_dir.get_provided_tags()

            for content in cert.content:
                if not content.content_type in ALLOWED_CONTENT_TYPES:
                    log.debug("Content type %s not allowed, skipping content: %s" % (
                        content.content_type, content.label))
                    continue

                all_tags_found = True
                for tag in content.required_tags:
                    if not tag in tags_we_have:
                        log.debug("Missing required tag '%s', skipping content: %s" % (
                            tag, content.label))
                        all_tags_found = False
                if all_tags_found:
                    lst.add(content)

        return lst

    def get_content(self, ent_cert, baseurl, ca_cert):
        lst = []

        for content in self.matching_content(ent_cert):
            content_id = content.label
            repo = Repo(content_id)
            repo['name'] = content.name
            if content.enabled:
                repo['enabled'] = "1"
            else:
                repo['enabled'] = "0"
            repo['baseurl'] = self.join(baseurl, self._use_release_for_releasever(content.url))

            # Extract the variables from thr url
            repo_parts = repo['baseurl'].split("/")
            repoid_vars = [part[1:] for part in repo_parts if part.startswith("$")]
            if repoid_vars:
                repo['ui_repoid_vars'] = " ".join(repoid_vars)

            # If no GPG key URL is specified, turn gpgcheck off:
            gpg_url = content.gpg
            if not gpg_url:
                repo['gpgkey'] = ""
                repo['gpgcheck'] = '0'
            else:
                repo['gpgkey'] = self.join(baseurl, gpg_url)
                # Leave gpgcheck as the default of 1

            repo['sslclientkey'] = self.get_key_path(ent_cert)
            repo['sslclientcert'] = ent_cert.path
            repo['sslcacert'] = ca_cert
            repo['metadata_expire'] = content.metadata_expire

            self._set_proxy_info(repo)

            if self.override_supported and self.apply_overrides:
                self._set_override_info(repo)

            lst.append(repo)
        return lst

    def _use_release_for_releasever(self, contenturl):
        # FIXME: release ala uep.getRelease should not be an int
        if self.release is None or \
           len(self.release) == 0:
            return contenturl
        return contenturl.replace("$releasever", "%s" % self.release)

    def _set_override_info(self, repo):
        # In the disconnected case, self.overrides will be an empty list
        for entry in self.overrides:
            if entry['contentLabel'] == repo.id:
                repo[entry['name']] = entry['value']

    def _set_proxy_info(self, repo):
        proxy = ""

        proxy_host = CFG.get('server', 'proxy_hostname')
        # proxy_port as string is fine here
        proxy_port = CFG.get('server', 'proxy_port')
        if proxy_host != "":
            proxy = "https://%s" % proxy_host
            if proxy_port != "":
                proxy = "%s:%s" % (proxy, proxy_port)

        # These could be empty string, in which case they will not be
        # set in the yum repo file:
        repo['proxy'] = proxy
        repo['proxy_username'] = CFG.get('server', 'proxy_user')
        repo['proxy_password'] = CFG.get('server', 'proxy_password')

    def join(self, base, url):
        if len(url) == 0:
            return url
        elif '://' in url:
            return url
        else:
            if (base and (not base.endswith('/'))):
                base = base + '/'
            if (url and (url.startswith('/'))):
                url = url.lstrip('/')
            return basejoin(base, url)

    def update_repo(self, old_repo, new_repo):
        """
        Checks an existing repo definition against a potentially updated
        version created from most recent entitlement certificates and
        configuration. Creates, updates, and removes properties as
        appropriate and returns the number of changes made. (if any)

        This method should only be used in disconnected cases!
        """
        if self.identity.is_valid() and self.override_supported:
            log.error("Can not update repos when registered!")
            raise UnsupportedOperationException()

        changes_made = 0

        for key, mutable, default in Repo.PROPERTIES:
            new_val = new_repo.get(key)

            # Mutable properties should be added if not currently defined,
            # otherwise left alone.
            if mutable:
                if (new_val is not None) and (not old_repo[key]):
                    if old_repo[key] == new_val:
                        continue
                    old_repo[key] = new_val
                    changes_made += 1

            # Immutable properties should be always be added/updated,
            # and removed if undefined in the new repo definition.
            else:
                if new_val is None or (new_val.strip() == ""):
                    # Immutable property should be removed:
                    if key in old_repo.keys():
                        del old_repo[key]
                        changes_made += 1
                    continue

                # Unchanged:
                if old_repo[key] == new_val:
                    continue

                old_repo[key] = new_val
                changes_made += 1

        return changes_made


class Repo(dict):
    # (name, mutable, default) - The mutability information is only used in disconnected cases
    PROPERTIES = (
        ('name', 0, None),
        ('baseurl', 0, None),
        ('enabled', 1, '1'),
        ('gpgcheck', 1, '1'),
        ('gpgkey', 0, None),
        ('sslverify', 1, '1'),
        ('sslcacert', 0, None),
        ('sslclientkey', 0, None),
        ('sslclientcert', 0, None),
        ('metadata_expire', 1, None),
        ('proxy', 0, None),
        ('proxy_username', 0, None),
        ('proxy_password', 0, None),
        ('ui_repoid_vars', 0, None),
    )

    def __init__(self, repo_id, existing_values=None):
        # existing_values is a list of 2-tuples
        existing_values = existing_values or []
        self.id = self._clean_id(repo_id)

        # used to store key order, so we can write things out in the order
        # we read them from the config.
        self._order = []

        for key, value in existing_values:
            # only set keys that have a non-empty value, to not clutter the
            # file.
            if value:
                self[key] = value

        # NOTE: This sets the above properties to the default values even if
        # they are not defined on disk. i.e. these properties will always
        # appear in this dict, but their values may be None.
        for k, m, d in self.PROPERTIES:
            if k not in self.keys():
                self[k] = d

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


class TidyWriter:

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


class RepoFile(ConfigParser):

    PATH = 'etc/yum.repos.d/'

    def __init__(self, name='redhat.repo'):
        ConfigParser.__init__(self)
        # note PATH get's expanded with chroot info, etc
        self.path = Path.join(self.PATH, name)
        self.repos_dir = Path.abs(self.PATH)
        self.manage_repos = 1
        if CFG.has_option('rhsm', 'manage_repos'):
            self.manage_repos = int(CFG.get('rhsm', 'manage_repos'))
        # Simulate manage repos turned off if no yum.repos.d directory exists.
        # This indicates yum is not installed so clearly no need for us to
        # manage repos.
        if not os.path.exists(self.repos_dir):
            log.warn("%s does not exist, turning manage_repos off." %
                    self.repos_dir)
            self.manage_repos = 0
        self.create()

    def exists(self):
        return os.path.exists(self.path)

    def read(self):
        ConfigParser.read(self, self.path)

    def write(self):
        if not self.manage_repos:
            log.debug("Skipping write due to manage_repos setting: %s" %
                    self.path)
            return
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

        for k, v in repo.items():
            ConfigParser.set(self, repo.id, k, v)

    def section(self, section):
        if self.has_section(section):
            return Repo(section, self.items(section))

    def create(self):
        if os.path.exists(self.path) or not self.manage_repos:
            return
        f = open(self.path, 'w')
        s = []
        s.append('#')
        s.append('# Certificate-Based Repositories')
        s.append('# Managed by (rhsm) subscription-manager')
        s.append('#')
        s.append('# *** This file is auto-generated.  Changes made here will be over-written. ***')
        s.append('# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***')
        s.append('#')
        s.append('# If this file is empty and this system is subscribed consider ')
        s.append('# a "yum repolist" to refresh available repos')
        s.append('#')
        f.write('\n'.join(s))
        f.close()
