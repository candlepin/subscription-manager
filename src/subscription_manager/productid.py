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
import time
import simplejson as json
import gettext
_ = gettext.gettext

from yum import YumBase
from gzip import GzipFile
from rhsm.certificate import ProductCertificate
from subscription_manager.certlib import Directory, ProductDirectory


class DatabaseDirectory(Directory):

    PATH = 'var/lib/rhsm'

    def __init__(self):
        Directory.__init__(self, self.PATH)
        self.create()


class ProductDatabase:

    def __init__(self):
        self.dir = DatabaseDirectory()
        self.content = {}
        self.create()

    def add(self, product, repo):
        self.content[product] = repo

    def delete(self, product):
        try:
            del self.content[product]
        except:
            pass

    def findRepo(self, product):
        return self.content.get(product)

    def create(self):
        if not os.path.exists(self.__fn()):
            self.write()

    def read(self):
        f = open(self.__fn())
        try:
            d = json.load(f)
            self.content = d
        except:
            pass
        f.close()

    def write(self):
        f = open(self.__fn(), 'w')
        try:
            json.dump(self.content, f, indent=2)
        except:
            pass
        f.close()

    def __fn(self):
        return self.dir.abspath('productid.js')


class ProductManager:

    REPO = 'from_repo'
    PRODUCTID = 'productid'

    def __init__(self):
        self.pdir = ProductDirectory()
        self.db = ProductDatabase()
        self.db.read()

    def update(self, yb=YumBase()):
        enabled = self.getEnabled(yb)
        active = self.getActive(yb)
        self.updateRemoved(active)
        self.updateInstalled(enabled, active)

    def updateInstalled(self, enabled, active):
        for cert, repo in enabled:
            if repo not in active:
                continue
            p = cert.getProduct()
            hash = p.getHash()
            if self.pdir.findByProduct(hash):
                continue
            fn = '%s.pem' % hash
            path = self.pdir.abspath(fn)
            print _('installing: %s') % fn
            cert.write(path)
            self.db.add(hash, repo)
            self.db.write()

    def updateRemoved(self, active):
        for cert in self.pdir.list():
            p = cert.getProduct()
            hash = p.getHash()
            repo = self.db.findRepo(hash)
            if repo is None:
                continue
            if repo in active:
                continue
            print _('deleting: %s') % cert.path
            cert.delete()
            self.db.delete(hash)
            self.db.write()

    def getActive(self, yb):
        active = set()
        start = time.time()
        packages = yb.pkgSack.returnPackages()
        for p in packages:
	    repo = p.repoid
            if repo in (None, 'installed'):
                continue
            active.add(repo)
        end = time.time()
        ms = (end - start) * 1000
        print _('duration: %d(ms)') % ms
        return active

    def getEnabled(self, yb):
        lst = []
        enabled = yb.repos.listEnabled()
        for repo in enabled:
            try:
                fn = repo.retrieveMD(self.PRODUCTID)
                cert = self.__getCert(fn)
                if cert is None:
                    continue
                lst.append((cert, repo.id))
            except:
                pass
        return lst

    def __getCert(self, fn):
        if fn.endswith('.gz'):
            f = GzipFile(fn)
        else:
            f = open(fn)
        try:
            pem = f.read()
            return ProductCertificate(pem)
        finally:
            f.close()

if __name__ == '__main__':
    pm = ProductManager()
    pm.update()
