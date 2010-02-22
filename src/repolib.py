#
# Copyright (C) 2005-2008 Red Hat, Inc.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# Jeff Ortel (jortel@redhat.com)
#
 
import os
from certlib import CertificateDirectory
from logutil import getLogger

log = getLogger(__name__)


class RepoLib:

    def update(self):
        repod = RepoFile()
        repod.read()
        valid = set()
        updates = 0
        products = self.products()
        for cont in self.content(products):
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

    def products(self):
        dir = CertificateDirectory()
        return dir.list()
    
    def content(self, products):
        unique = set()
        products.sort()
        products.reverse()
        for product in products:
            for ent in product.getEntitlements():
                id = ent.getName()
                repo = Repo(id)
                repo['name'] = ent.getDescription()
                repo['baseurl'] = ent.getUrl()
                repo['sslclientkey'] = CertificateDirectory.keypath()
                repo['sslclientcert'] = product.path
                unique.add(repo)
        return unique 


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
        if len(self.section) > 1:
            del self.section[None]
        f.close()
        
    def newsection(self, name):
        return {}
        
    def __getitem__(self, name):
        return self.section.get(name)

   
class Repo(dict):
    
    # (name, mutable, default)
    KEYS = (
        ('name', 0, None),
        ('baseurl', 1, None),
        ('enabled', 0, '1'),
        ('gpgcheck', 0, '0'),
        ('gpgkey', 1, None),
        ('sslverify', 0, '1'),
        ('sslclientkey', 1, None),
        ('sslclientcert', 1, None),
    )
    
    def __init__(self, id):
        self.id = id
        for k,m,d in self.KEYS:
            self[k] = d
    
    def update(self, other):
        count = 0
        for k,m,d in self.KEYS:
            v = other.get(k)
            if m:
                if v is None:
                    continue
                if self[k] == v:
                    continue
                self[k] = v
                count += 1
        return count
        
    def __str__(self):
        s = []
        s.append('[%s]' % self.id)
        for k,m,d in self.KEYS:
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

