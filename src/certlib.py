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
from datetime import timedelta
from config import initConfig
from connection import UEPConnection
from certificate import *
from lock import Lock
from logutil import getLogger


log = getLogger(__name__)

import gettext
_ = gettext.gettext


class ActionLock(Lock):

    PATH = '/var/run/subsys/rhsm/cert.pid'

    def __init__(self):
        Lock.__init__(self, self.PATH)


class CertLib:

    def __init__(self, lock=ActionLock()):
        self.lock = lock

    def update(self):
        lock = self.lock
        lock.acquire()
        try:
            action = UpdateAction()
            return action.perform()
        finally:
            lock.release()

    def add(self, *bundles):
        lock = self.lock
        lock.acquire()
        try:
            action = AddAction()
            return action.perform(bundles)
        finally:
            lock.release()

    def delete(self, *serialNumbers):
        lock = self.lock
        lock.acquire()
        try:
            action = DeleteAction()
            return action.perform(serialNumbers)
        finally:
            lock.release()

class Action:

    def __init__(self):
        self.entdir = EntitlementDirectory()

    def build(self, bundle):
        keypem = bundle['key']
        crtpem = bundle['cert']
        key = Key(keypem)
        cert = EntitlementCertificate(crtpem)
        bogus = cert.bogus()
        if bogus:
            bogus.insert(0, _('Reasons(s):'))
            raise Exception, '\n - '.join(bogus)
        return (key, cert)


class AddAction(Action):

    def perform(self, *bundles):
        for bundle in bundles:
            try:
                key,cert = self.build(bundle)
            except Exception, e:
                log.error(
                    'Bundle not loaded:\n%s\n%s',
                    bundle,
                    e)
        return self


class DeleteAction(Action):

    def perform(self, *serialNumbers):
        for sn in serialNumbers:
            cert = self.entdir.find(sn)
            if cert is None:
                continue
            cert.delete()
        return self


class UpdateAction(Action):

    def perform(self):
        try:
            uep = UEP()
        except Disconnected:
            log.info('Disconnected, not updated')
            return 0
        report = UpdateReport()
        local = self.getLocal(report)
        expected = self.getExpected(uep, report)
        missing, rogue = self.bashSerials(local, expected, report)
        self.delete(rogue, report)
        self.install(uep, missing, report)
        self.purgeExpired(report)
        log.info('updated:\n%s', report)
        return report.updates()

    def getLocal(self, report):
        local = {}
        #certificates in grace period were being renamed everytime.
        #this makes sure we don't try to re-write certificates in
        #grace period
        for valid in self.entdir.listValid(grace_period=True):
            sn = valid.serialNumber()
            report.valid.append(sn)
            local[sn] = valid
        return local

    def getExpected(self, uep, report):
        exp = uep.getCertificateSerials()
        report.expected = exp
        return exp

    def bashSerials(self, local, expected, report):
        missing = []
        rogue = []
        for sn in expected:
            if not sn in local:
                missing.append(sn)
        for sn in local:
            if not sn in expected:
                cert = local[sn]
                rogue.append(cert)
        return (missing, rogue)

    def delete(self, rogue, report):
        for cert in rogue:
            cert.delete()
            report.rogue.append(cert)

    def install(self, uep, serials, report):
        br = Writer()
        for bundle in uep.getCertificatesBySerial(serials):
            try:
                key,cert = self.build(bundle)
                br.write(key, cert)
                report.added.append(cert)
            except Exception, e:
                log.error(
                    'Bundle not loaded:\n%s\n%s',
                    bundle,
                    e)

    def purgeExpired(self, report):
        for cert in self.entdir.listExpired():
            if self.mayLinger(cert):
                report.expnd.append(cert)
                continue
            report.expd.append(cert)
            cert.delete()
    
    def mayLinger(self, cert):
        return cert.validWithGracePeriod()


class Writer:

    def __init__(self):
        self.entdir = EntitlementDirectory()

    def write(self, key, cert):
        path = self.entdir.keypath()
        key.write(path)
        sn = cert.serialNumber()
        path = self.entdir.productpath()
        fn = self.__ufn(path, sn)
        path = Path.join(path, fn)
        cert.write(path)
        
    def __ufn(self, path, sn):
        n = 1
        name = str(sn)
        fn = None
        while True:
            fn = '%s.pem' % name
            path = Path.join(path, fn)
            if os.path.exists(path):
                name += '(%d)' % n
                n += 1
            else:
                break
        return fn


class UEP(UEPConnection):
    
    @classmethod
    def consumerId(cls):
        try:
            cid = ConsumerIdentity.read()
            return cid.getConsumerId()
        except:
            raise Disconnected()

    def __init__(self):
        cfg = initConfig()
        host = cfg['hostname'] or "localhost"
        port = cfg['port']
        cert = ConsumerIdentity.certpath()
        key = ConsumerIdentity.keypath()
        UEPConnection.__init__(self, host, ssl_port=port, cert_file=cert,
                               key_file=key)
        self.uuid = self.consumerId()
        
    def getCertificateSerials(self):
        result = []
        reply = UEPConnection.getCertificateSerials(self, self.uuid)
        for d in reply:
            sn = d['serial']
            result.append(sn)
        return result

    def getCertificatesBySerial(self, snList):
        result = []
        if snList:
            snList = [str(sn) for sn in snList]
            reply = UEPConnection.getCertificates(self, self.uuid, serials=snList)
            for cert in reply:
                result.append(cert)
        return result


class Disconnected(Exception):
    pass


class Path:

    ROOT = '/'

    @classmethod
    def join(cls, a, b):
        path = os.path.join(a, b)
        return cls.abs(path)

    @classmethod
    def abs(cls, path):
        if os.path.isabs(path):
            return path
        else:
            return os.path.join(cls.ROOT, path)

    @classmethod
    def isdir(cls, path):
        return os.path.isdir(path)
        

class Directory:
    
    def __init__(self, path):
        self.path = Path.abs(path)
        
    def listAll(self):
        all = []
        for fn in os.listdir(self.path):
            p = (self.path, fn)
            all.append(p)
        return all

    def list(self):
        files = []
        for p,fn in self.listAll():
            path = self.abspath(fn)
            if Path.isdir(path):
                continue
            else:
                files.append((p,fn))
        return files
    
    def listdirs(self):
        dir = []
        for p,fn in self.listAll():
            path = self.abspath(fn)
            if Path.isdir(path):
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
            path = self.abspath(x)
            if Path.isdir(path):
                d = Directory(path)
                d.delete()
            else:
                os.unlink(path)
                
    def abspath(self, path):
        return Path.join(self.path, path)
    
    def __str__(self):
        return self.path
    
    
class CertificateDirectory(Directory):

    def __init__(self, path):
        Directory.__init__(self, path)
        self.create()

    def list(self):
        listing = []
        factory = self.Factory(self.certClass())
        for p,fn in Directory.list(self):
            if not fn.endswith('.pem'):
                continue
            path = self.abspath(fn)
            factory.append(path, listing)
        return listing

    def listValid(self, grace_period=False):
        valid = []
        for c in self.list():
            if grace_period:
                if c.validWithGracePeriod():
                    valid.append(c)
            elif c.valid():
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

    def findByProduct(self, hash):
        for c in self.list():
            p = c.getProduct()
            if p.getHash() == hash:
                return c
        return None

    def certClass(self):
        return Certificate

    class Factory:

        def __init__(self, cls):
            self.cls = cls

        def append(self, path, certlist):
            try:
                cert = self.cls()
                cert.read(path)
                bogus = cert.bogus()
                if bogus:
                    bogus.insert(0, _('Reason(s):'))
                    raise Exception, '\n - '.join(bogus)
                certlist.append(cert)
            except Exception, e:
                log.error(
                    'File: %s, not loaded\n%s',
                    path,
                    e)


class ProductDirectory(CertificateDirectory):
    
    PATH = 'etc/pki/product'
    KEY = 'key.pem'
    
    def __init__(self):
        CertificateDirectory.__init__(self, self.PATH)
        
    def certClass(self):
        return ProductCertificate


class EntitlementDirectory(CertificateDirectory):
    
    PATH = 'etc/pki/entitlement'
    KEY = 'key.pem'
    PRODUCT = 'product'
    
    @classmethod
    def keypath(cls):
        return Path.join(cls.PATH, cls.KEY)

    @classmethod
    def productpath(cls):
        return Path.join(cls.PATH, cls.PRODUCT)

    def __init__(self):
        CertificateDirectory.__init__(self, self.productpath())

    def certClass(self):
        return EntitlementCertificate


class ConsumerIdentity:
    
    PATH = 'etc/pki/consumer'
    KEY = 'key.pem'
    CERT = 'cert.pem'
    
    @classmethod
    def keypath(cls):
        return Path.join(cls.PATH, cls.KEY)
    
    @classmethod
    def certpath(cls):
        return Path.join(cls.PATH, cls.CERT)
    
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

    @classmethod
    def existsAndValid(cls):
        from M2Crypto import X509
        if cls.exists():
            try:
                cls.read()
                return True
            except X509.X509Error, e:
                log.error(e)
                log.warn('possible certificate corruption')
        return False

    
    def __init__(self, keystring, certstring):
        self.key = keystring
        self.cert = certstring
        self.x509 = Certificate(certstring)
        
    def getConsumerId(self):
        subject = self.x509.subject()
        return subject.get('CN')

    def getConsumerName(self):
        altName = self.x509.alternateName()
        return altName.replace("DirName:/CN=", "")
        
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
            os.unlink(path)
        path = self.certpath()
        if os.path.exists(path):
            os.unlink(path)
    
    def __mkdir(self):
        path = Path.abs(self.PATH)
        if not os.path.exists(path):
            os.mkdir(path)

    def __str__(self):
        return 'consumer: name="%s", uuid=%s' % \
            (self.getConsumerName(),
             self.getConsumerId())


class UpdateReport:

    def __init__(self):
        self.valid = []
        self.expected = []
        self.added = []
        self.rogue = []
        self.expd = []
        self.expnd = []

    def updates(self):
        return ( len(self.added)
                +len(self.rogue)
                +len(self.expd) )

    def write(self, s, title, certificates):
        indent = '  '
        s.append(title)
        if certificates:
            for c in certificates:
                p = c.getProduct()
                s.append('%s[sn:%d (%s,) @ %s]' % \
                    (indent,
                     c.serialNumber(),
                     p.getName(),
                     c.path))
        else:
            s.append('%s<NONE>' % indent)

    def __str__(self):
        s = []
        s.append(_('Total updates: %d') % self.updates())
        s.append(_('Found (local) serial# %s') % self.valid)
        s.append(_('Expected (UEP) serial# %s') % self.expected)
        self.write(s, _('Added (new)'), self.added)
        self.write(s, _('Deleted (rogue):'), self.rogue)
        self.write(s, _('Expired (not deleted):'), self.expnd)
        self.write(s, _('Expired (deleted):'), self.expd)
        return '\n'.join(s)


def main():
    print _('Updating Red Hat certificates')
    certlib = CertLib()
    updates = certlib.update()
    print _('%d updates required') % updates
    print _('done')
        
if __name__ == '__main__':
    main()
