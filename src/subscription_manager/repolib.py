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

import os
import string
import logging
from urllib import basejoin
from iniparse import ConfigParser as Parser

from rhsm.config import initConfig

from certlib import Path, EntitlementDirectory, \
        ProductDirectory, ActionLock, DataLib

log = logging.getLogger('rhsm-app.' + __name__)


class RepoLib(DataLib):

    def __init__(self, lock=ActionLock(), uep=None):
        DataLib.__init__(self, lock, uep)

    def _do_update(self):
        action = UpdateAction(uep=self.uep)
        return action.perform()



class UpdateAction:

    def __init__(self, uep=None, ent_dir=None, prod_dir=None):
        if ent_dir:
            self.ent_dir = ent_dir
        else:
            self.ent_dir = EntitlementDirectory()

        if prod_dir:
            self.prod_dir = prod_dir
        else:
            self.prod_dir = ProductDirectory()

        self.uep = uep

    def perform(self):
        # Load the RepoFile from disk, this contains all our managed yum repo sections:
        repo_file = RepoFile()
        repo_file.read()
        valid = set()
        updates = 0

        # Iterate content from entitlement certs, and update/create/delete each section
        # in the RepoFile as appropriate:
        for cont in self.get_unique_content():
            valid.add(cont.id)
            existing = repo_file.section(cont.id)
            if existing is None:
                updates += 1
                repo_file.add(cont)
                continue
            updates += existing.update(cont)
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
        # Though they are expired, we keep repos around that are within their
        # grace period, as they will still allow access to the content.
        ent_certs = self.ent_dir.listValid(grace_period=True)
        cfg = initConfig()
        baseurl = cfg.get('rhsm', 'baseurl')
        ca_cert = cfg.get('rhsm', 'repo_ca_cert')
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

    def get_content(self, ent_cert, baseurl, ca_cert):
        lst = []
        cfg = initConfig()

        tags_we_have = self.prod_dir.get_provided_tags()

        for content in ent_cert.getContentEntitlements():

            all_tags_found = True
            for tag in content.getRequiredTags():
                if not tag in tags_we_have:
                    log.debug("Missing required tag '%s', skipping content: %s" % (
                        tag, content.getLabel()))
                    all_tags_found = False
            if not all_tags_found:
                # Skip this content:
                continue

            content_id = content.getLabel()
            repo = Repo(content_id)
            repo['name'] = content.getName()
            repo['enabled'] = content.getEnabled()
            repo['baseurl'] = self.join(baseurl, content.getUrl())
            repo['gpgkey'] = self.join(baseurl, content.getGpg())
            repo['sslclientkey'] = self.get_key_path(ent_cert)
            repo['sslclientcert'] = ent_cert.path
            repo['sslcacert'] = ca_cert
            repo['metadata_expire'] = content.getMetadataExpire()

            self._set_proxy_info(repo, cfg)
            lst.append(repo)
        return lst

    def _set_proxy_info(self, repo, cfg):
        proxy = ""

        proxy_host = cfg.get('server', 'proxy_hostname')
        proxy_port = cfg.get('server', 'proxy_port')
        if proxy_host != "":
            proxy = "http://%s" % proxy_host
            if proxy_port != "":
                proxy = "%s:%s" % (proxy, proxy_port)

        # These could be empty string, in which case they will not be
        # set in the yum repo file:
        repo['proxy'] = proxy
        repo['proxy_username'] = cfg.get('server', 'proxy_user')
        repo['proxy_password'] = cfg.get('server', 'proxy_password')

    def join(self, base, url):
        if '://' in url:
            return url
        else:
            if (base and (not base.endswith('/'))):
                base = base + '/'
            if (url and (url.startswith('/'))):
                url = url.lstrip('/')
            return basejoin(base, url)


class Repo(dict):

    # (name, mutable, default)
    PROPERTIES = (
        ('name', 0, None),
        ('baseurl', 0, None),
        ('enabled', 1, '1'),
        ('gpgcheck', 0, '1'),
        ('gpgkey', 0, None),
        ('sslverify', 0, '1'),
        ('sslcacert', 0, None),
        ('sslclientkey', 0, None),
        ('sslclientcert', 0, None),
        ('metadata_expire', 1, None),
        ('proxy', 0, None),
        ('proxy_username', 0, None),
        ('proxy_password', 0, None),
    )

    def __init__(self, repo_id):
        self.id = self._clean_id(repo_id)
        # NOTE: This sets the above properties to the default values even if
        # they are not defined on disk. i.e. these properties will always
        # appear in this dict, but their values may be None.
        for k, m, d in self.PROPERTIES:
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
        lst = []
        for k, m, d in self.PROPERTIES:
            if not k in self:
                continue
            v = self[k]
            # Skip anything set to 'None', as this is likely not intended for
            # a yum repo file. None can result here if the default is None,
            # or the entitlement certificate did not have the value set.
            if v:
                lst.append((k, v))
        return tuple(lst)

    def update(self, new_repo):
        """
        Checks an existing repo definition against a potentially updated
        version created from most recent entitlement certificates and
        configuration. Creates, updates, and removes properties as
        appropriate and returns the number of changes made. (if any)
        """
        changes_made = 0

        for key, mutable, default in self.PROPERTIES:
            new_val = new_repo.get(key)

            # Mutable properties should be added if not currently defined,
            # otherwise left alone.
            if mutable:
                if (new_val is not None) and (not self[key]):
                    if self[key] == new_val:
                        continue
                    self[key] = new_val
                    changes_made += 1

            # Immutable properties should be always be added/updated,
            # and removed if undefined in the new repo definition.
            else:
                if new_val is None or (new_val.strip() == ""):
                    # Immutable property should be removed:
                    if key in self.keys():
                        del self[key]
                        changes_made += 1
                    continue

                # Unchanged:
                if self[key] == new_val:
                    continue

                self[key] = new_val
                changes_made += 1

        return changes_made

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


class RepoFile(Parser):

    PATH = 'etc/yum.repos.d/'

    def __init__(self, name='redhat.repo'):
        Parser.__init__(self)
        self.path = Path.join(self.PATH, name)
        self.create()

    def read(self):
        r = Reader(self.path)
        Parser.readfp(self, r)

    def write(self):
        f = open(self.path, 'w')
        Parser.write(self, f)
        f.close()

    def add(self, repo):
        self.add_section(repo.id)
        self.update(repo)

    def delete(self, section):
        return self.remove_section(section)

    def update(self, repo):
        # Need to clear out the old section to allow unsetting options:
        self.remove_section(repo.id)
        self.add_section(repo.id)
        for k, v in repo.items():
            Parser.set(self, repo.id, k, v)

    def section(self, section):
        if self.has_section(section):
            repo = Repo(section)
            for k, v in self.items(section):
                repo[k] = v
            return repo

    def create(self):
        if os.path.exists(self.path):
            return
        f = open(self.path, 'w')
        s = []
        s.append('#')
        s.append('# Certificate-Based Repositories')
        s.append('# Managed by (rhsm) subscription-manager')
        s.append('#')
        f.write('\n'.join(s))
        f.close()


class Reader:

    def __init__(self, path):
        f = open(path)
        bfr = f.read()
        self.idx = 0
        self.lines = bfr.split('\n')
        f.close()

    def readline(self):
        nl = 0
        i = self.idx
        eof = len(self.lines)
        while 1:
            if i == eof:
                return
            ln = self.lines[i]
            i += 1
            if not ln:
                nl += 1
            else:
                break
        if nl:
            i -= 1
            ln = '\n'
        self.idx = i
        return ln


def main():
    print 'Updating Certificate based repositories'
    repolib = RepoLib()
    updates = repolib.update()
    print '%d updates required' % updates
    print 'done'

if __name__ == '__main__':
    main()
