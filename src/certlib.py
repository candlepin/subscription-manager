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
from config import initConfig
from connection import UEPConnection
from certificate import ProductCertificate, Bundle
from logutil import getLogger


log = getLogger(__name__)


class CertLib:
    
    def __init__(self):
        self.entdir = EntitlementDirectory()
    
    def update(self):
        updates = 0
        snlist = []
        for valid in self.entdir.listValid():
            sn = valid.serialNumber()
            snlist.append(sn)
        uep = UEP()
        for st in uep.syncCertificates(snlist):
            sn = st['serialNumber']
            status = st['status']
            bundle = st.get('certificate')
            if status == 'VALID':
                continue
            if status in ('NEW','REPLACE'):
                updates += 1
                self.__write(Bundle.split(bundle))
                continue
            if status == 'REVOKE':
                updates += 1
                cert = self.entdir.find(sn)
                os.remove(cert.path)
                continue
        for c in self.entdir.listExpired():
            os.remove(c.path)
        return updates
        
    def add(self, *bundles):
        for b in bundles:
            self.__write(Bundle.split(b))
        return self
    
    def __write(self, bundle):
        path = self.entdir.keypath()
        f = open(path, 'w')
        f.write(bundle.key)
        f.close()
        cert = ProductCertificate(bundle.cert)
        product = cert.getProduct()
        path = self.entdir.productpath()
        fn = '%s.pem' % product.getName()
        path = os.path.join(path, fn)
        f = open(path)
        f.write(bundle.cert)
        f.close()
    

class UEP(UEPConnection):
    
    def __init__(self):
        cfg = initConfig()
        host = cfg['hostname']
        port = cfg['port']
        UEPConnection.__init__(self, host, port)
        
    def syncCertificates(self, serialnumbers):
        reply = []
        for sn in serialnumbers:
            d = {}
            d['serialNumber'] = sn
            d['status'] = 'VALID'
            reply.append(d)
        return reply


class Directory:
    
    def __init__(self, path):
        self.path = path
        
    def list(self):
        entries = []
        for fn in os.listdir(self.path):
            p = (self.path, fn)
            entries.append(p)
        return entries
    
    def listdirs(self):
        dir = []
        for p,fn in self.list():
            path = os.path.join(p, fn)
            if os.path.isdir(path):
                dir.append(Directory(path))
        return dir
    
    def create(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            
    def delete(self):
        self.clean()
        os.rmdir(self.path)
            
    def clean(self):
        for x in os.listdir(self.path):
            path = os.path.join(self.path, x)
            if os.path.isdir(path):
                d = Directory(path)
                d.delete()
            else:
                os.remove(path)
    
    def __str__(self):
        return self.path

    
class EntitlementDirectory(Directory):
    
    ROOT = '/etc/pki/entitlement'
    KEY = 'key.pem'
    PRODUCT = 'product'
    
    @classmethod
    def keypath(cls):
        return os.path.join(cls.ROOT, cls.KEY)
    
    @classmethod
    def productpath(cls):
        return os.path.join(cls.ROOT, cls.PRODUCT)
    
    def __init__(self):
        Directory.__init__(self, self.productpath())
        self.create()
        
    def list(self):
        all = []
        for p,fn in Directory.list(self):
            if not fn.endswith('.pem'):
                continue
            path = os.path.join(p, fn)
            crt = ProductCertificate.read(path)
            crt.path = path
            all.append(crt)
        return all
    
    def listValid(self):
        valid = []
        for c in self.list():
             if c.valid():
                valid.append(c)
        return valid
    
    def listExpired(self):
        expired = []
        for c in self.list():
             if not c.valid():
                expired.append(c)
        return expired
    
    def find(self, sn):
        for c in self.list():
            if c.serialNumber() == sn:
                return c
        return None
    
    
class ProductDirectory(Directory):
    
    PATH = '/etc/pki/product'
    
    def __init__(self):
        Directory.__init__(self, self.PATH)
        self.create()
        
    def list(self):
        all = []
        for p,fn in Directory.list(self):
            if not fn.endswith('.pem'):
                continue
            path = os.path.join(p, fn)
            crt = ProductCertificate.read(path)
            crt.path = path
            all.append(crt)
        return all
    
    def listValid(self):
        valid = []
        for c in self.list():
             if c.valid():
                valid.append(c)
        return valid
    
    def listExpired(self):
        expired = []
        for c in self.list():
             if not c.valid():
                expired.append(c)
        return expired
    

class ConsumerIdentity:
    
    LOCATION = '/etc/pki/consumer'
    KEY = 'key.pem'
    CERT = 'cert.pem'
    
    @classmethod
    def keypath(cls):
        return os.path.join(cls.LOCATION, cls.KEY)
    
    @classmethod
    def certpath(cls):
        return os.path.join(cls.LOCATION, cls.CERT)
    
    @classmethod
    def read(cls):
        self.__mkdir()
        f = open(self.keypath())
        key = f.read()
        f.close()
        f = open(self.certpath())
        cert = f.read()
        f.close()
        return ConsumerIdentity(key, cert) 
    
    def __init__(self, keystring, certstring):
        self.key = keystring
        self.cert = certstring
        
    def getConsumerId(self):
        return '99'
        
    def write(self):
        self.__mkdir()
        f = open(self.keypath(), 'w')
        f.write(self.key)
        f.close()
        f = open(self.certpath(), 'w')
        f.write(self.cert)
        f.close()
    
    def __mkdir(self):
        if not os.path.exists(self.LOCATION):
            os.mkdir(path)


def main():
    print 'Updating Red Hat certificates'
    certlib = CertLib()
    updates = certlib.update()
    print '%d updates required' % updates
    print 'done'
        
if __name__ == '__main__':
    main()