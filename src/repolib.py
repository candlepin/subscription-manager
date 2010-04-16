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
from urllib import basejoin
from config import initConfig
from certlib import EntitlementDirectory, ActionLock
from logutil import getLogger

log = getLogger(__name__)


class RepoLib:

    def update(self):
        lock = ActionLock()
        try:
            update = UpdateAction()
            return update.perform()
        finally:
            lock.release()


class Action:

    def __init__(self):
        self.entdir = EntitlementDirectory()
        
        
class UpdateAction(Action):
    
    SNAPSHOT = '/tmp/rhsm/entitlement/snapshot.p'

    def perform(self):
        repod = RepoFile()
        repod.read()
        valid = set()
        updates = 0
        products = self.entdir.listValid()
        for cont in self.getUniqueContent():
            name = cont.id
            valid.add(name)
            existing = repod[name]
            if existing is None:
                updates += 1
                repod[name] = cont
                continue
            updates += existing.update(cont)
        delete = []
        for name in repod.section:
            if name not in valid:
                delete.append(name)
        for name in delete:
            updates += 1
            del repod.section[name]
        repod.write()
        return updates
    
    def getUniqueContent(self):
        unique = set()
        products = self.entdir.listValid()
        products.sort()
        products.reverse()
        cfg = initConfig()
        baseurl = cfg['baseurl']
        for product in products:
            for r in self.getContent(product, baseurl):
                unique.add(r)
        return unique
    
    def getContent(self, product, baseurl):
        lst = []
        for ent in product.getContentEntitlements():
            id = ent.getLabel()
            repo = Repo(id)
            repo['name'] = ent.getName()
            repo['enabled'] = ent.getEnabled()
            repo['baseurl'] = self.join(baseurl, ent.getUrl())
            repo['gpgkey'] = self.join(baseurl, ent.getGpg())
            repo['sslclientkey'] = EntitlementDirectory.keypath()
            repo['sslclientcert'] = product.path
            lst.append(repo)
        return lst
    
    def join(self, base, url):
        if '://' in url:
            return url
        else:
            return basejoin(base, url)


class Reader:

    def __init__(self):
        self.section = {}
        self.section[None] = self.newsection(None)

    def read(self, path):
        f = open(path)
        section = self.section[None]
        for line in f.readlines():
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                name = line[1:-1].strip()
                section = self.newsection(name)
                self.section[name] = section
                continue
            if line.startswith('#'):
                continue
            part = line.split('=', 1)
            if len(part) != 2:
                continue
            name = part[0].strip()
            value = part[1].strip()
            section[name] = value
        f.close()
        
    def newsection(self, name):
        return {}
        
    def __getitem__(self, name):
        return self.section.get(name)

   
class Repo(dict):
    
    CA = '/usr/share/rhn/RHNS-CA-CERT'
    
    # (name, mutable, default)
    KEYS = (
        ('name', 0, None),
        ('baseurl', 0, None),
        ('enabled', 1, '1'),
        ('gpgcheck', 0, '1'),
        ('gpgkey', 0, None),
        ('sslverify', 0, '1'),
        ('sslcacert', 0, CA),
        ('sslclientkey', 0, None),
        ('sslclientcert', 0, None),
    )

    @classmethod
    def ord(cls, key):
        i = 0
        for k,m,d in cls.KEYS:
            if k == key:
                return i
            i += 1
        return 0x64
    
    def __init__(self, id):
        self.id = id
        for k,m,d in self.KEYS:
            self[k] = d
    
    def update(self, other):
        count = 0
        for k,m,d in self.KEYS:
            v = other.get(k)
            if not m:
                if v is None:
                    continue
                if self[k] == v:
                    continue
                self[k] = v
                count += 1
        return count

    def sorted(self):
        def cmpfn(a,b):
            n1 = Repo.ord(a)
            n2 = Repo.ord(b)
            return (n1-n2)
        return sorted(self.keys(), cmp=cmpfn)
        
    def __str__(self):
        s = []
        s.append('[%s]' % self.id)
        for k in self.sorted():
            v = self.get(k)
            if v is None:
                continue
            s.append('%s=%s' % (k, v))

        return '\n'.join(s)
    
    def __repr__(self):
        s = []
        for k,m,d in self.KEYS:
            v = self.get(k)
            s.append('%s=%s' % (k, v))
        return '\n'.join(s)
        
    def __eq__(self, other):
        return ( self.id == other.id )
    
    def __hash__(self):
        return hash(self.id)


class RepoFile(Reader):
    
    PATH = '/etc/yum.repos.d/'
    
    def __init__(self, name='redhat.repo'):
        Reader.__init__(self)
        self.path = os.path.join(self.PATH, name)
        self.create()
        
    def newsection(self, name):
        return Repo(name)
    
    def read(self):
        Reader.read(self, self.path)
        del self.section[None]
        
    def write(self):
        f = open(self.path, "w")
        f.write(str(self))
        f.close()
        
    def create(self):
        if not os.path.exists(self.path):
            f = open(self.path, 'w')
            f.close()
        
    def __setitem__(self, name, value):
        self.section[name] = value
        
    def __str__(self):
        s = []
        s.append('#')
        s.append('# Red Hat Repositories')
        s.append('# managed by subscription-manager')
        s.append('#\n')
        for name, repo in self.section.items():
            s.append(str(repo))
            s.append('')
        return '\n'.join(s)


def main():
    print 'Updating Red Hat repository'
    repolib = RepoLib()
    updates = repolib.update()
    print '%d updates required' % updates
    print 'done'
        
if __name__ == '__main__':
    main()

