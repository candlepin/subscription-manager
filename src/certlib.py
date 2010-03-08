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
import re
from datetime import datetime as dt
from datetime import timedelta
from config import initConfig
from connection import UEPConnection
from certificate import *
from lock import Lock
from logutil import getLogger


log = getLogger(__name__)


class CertLib:
    
    LINGER = timedelta(days=30)

    def update(self):
        lock = ActionLock()
        try:
            lock.acquire()
            update = UpdateAction()
            return update.perform()
        finally:
            lock.release()

    def add(self, *bundles):
        lock = ActionLock()
        try:
            lock.acquire()
            add = AddAction()
            return add.perform(bundles)
        finally:
            lock.release()


class ActionLock(Lock):

    PATH = '/var/run/subsys/rhsm/cert.pid'

    def __init__(self):
        Lock.__init__(self, self.PATH)


class Action:

    def __init__(self):
        self.entdir = EntitlementDirectory()


class AddAction(Action):

    def perform(self, *bundles):
        writer = Writer()
        for b in bundles:
            writer.write(b)
        return self


class UpdateAction(Action):

    LINGER = timedelta(days=30)
    
    def perform(self):
        updates = 0
        local = {}
        for valid in self.entdir.listValid():
            sn = valid.serialNumber()
            local[sn] = valid
        uep = UEP()
        expected = uep.getCertificateSerials()
        new = []
        for sn in expected:
            if not sn in local:
                new.append(sn)
        for sn in local:
            if not sn in expected:
                updates += 1
                os.remove(local[sn].path)
        writer = Writer()
        for bundle in uep.getCertificatesBySerial(new):
            updates += 1
            writer.write(bundle)
        for c in self.entdir.listExpired():
            if self.mayLinger(c):
                continue
            updates += 1
            os.remove(c.path)
        return updates
    
    def mayLinger(self, cert):
        valid = cert.validRange()
        end = valid.end()
        graceperoid = dt.utcnow()+self.LINGER
        return ( end < graceperoid )


class Writer:

    def __init__(self):
        self.entdir = EntitlementDirectory()

    def write(self, bundle):
        keypem = bundle['key']
        crtpem = bundle['cert']
        path = self.entdir.keypath()
        f = open(path, 'w')
        f.write(keypem)
        f.close()
        cert = EntitlementCertificate(crtpem)
        product = cert.getProduct()
        path = self.entdir.productpath()
        fn = self.__ufn(path, product)
        path = os.path.join(path, fn)
        f = open(path, 'w')
        f.write(crtpem)
        f.close()
        
    def __ufn(self, path, product):
        n = 1
        name = product.getName()
        name = re.sub('\s+', '', name)
        fn = None
        while True:
            fn = '%s.pem' % name
            path = os.path.join(path, fn)
            if os.path.exists(path):
                name += str(n)
                n += 1
            else:
                break
        return fn


class UEP(UEPConnection):
    
    def __init__(self):
        cfg = initConfig()
        host = cfg['hostname']
        port = cfg['port']
        UEPConnection.__init__(self, host, port)
        
    def getCertificateSerials(self):
        uuid = self.consumerId()
        if uuid is None:
            return ()
        expected = []
        for sn in UEPConnection.getCertificateSerials(self, uuid):
            expected.append(int(sn))
        return expected

    def getCertificatesBySerial(self, snList):
        uuid = self.consumerId()
        if uuid is None:
            return ()
        return UEPConnection.getCertificatesBySerial(self, uuid, snList)
        
    def consumerId(self):
        try:
            cid = ConsumerIdentity.read()
            return cid.getConsumerId()
        except:
            pass
        

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
            crt = EntitlementCertificate.read(path)
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
        f = open(cls.keypath())
        key = f.read()
        f.close()
        f = open(cls.certpath())
        cert = f.read()
        f.close()
        return ConsumerIdentity(key, cert)

    @classmethod
    def exists(cls):
        return ( os.path.exists(cls.keypath()) and \
                 os.path.exists(cls.certpath()) )
    
    def __init__(self, keystring, certstring):
        self.key = keystring
        self.cert = certstring
        
    def getConsumerId(self):
        cert = Certificate(self.cert)
        subject = cert.subject()
        return subject.get('CN')
        
    def write(self):
        self.__mkdir()
        f = open(self.keypath(), 'w')
        f.write(self.key)
        f.close()
        f = open(self.certpath(), 'w')
        f.write(self.cert)
        f.close()
        
    def delete(self):
        path = self.keypath()
        if os.path.exists(path):
            os.remove(path)
        path = self.certpath()
        if os.path.exists(path):
            os.remove(path)
    
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
