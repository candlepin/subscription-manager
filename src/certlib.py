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
import syslog
from datetime import timedelta, datetime
from config import initConfig
from connection import UEPConnection
from certificate import *
from lock import Lock
from logutil import getLogger
from config import initConfig


log = getLogger(__name__)

import gettext
_ = gettext.gettext

cfg = initConfig()


def system_log(message, priority=syslog.LOG_NOTICE):
	syslog.openlog("subscription-manager")
	syslog.syslog(priority, message)

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
            raise Exception('\n - '.join(bogus))
        return (key, cert)


class AddAction(Action):

    def perform(self, *bundles):
        for bundle in bundles:
            try:
                key, cert = self.build(bundle)
            except Exception, e:
                log.exception(e)
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
        uep = UEP()
        report = UpdateReport()
        local = self.getLocal(report)
        expected = self.getExpected(uep, report)
        missing, rogue = self.bashSerials(local, expected, report)
        self.delete(rogue, report)
        exceptions = self.install(uep, missing, report)
        self.purgeExpired(report)
        log.info('certs updated:\n%s', report)
        self.syslogResults(report)
        return (report.updates(), exceptions)

    def syslogResults(self, report):
        for cert in report.added:
            system_log("Added subscription for '%s' contract '%s'" % \
                (cert.getOrder().getName(), cert.getOrder().getContract()))
        for cert in report.rogue:
            system_log("Removed subscription for '%s' contract '%s'" % \
                (cert.getOrder().getName(), cert.getOrder().getContract()))
        for cert in report.expnd:
            system_log("Expired subscription for '%s' contract '%s'" % \
                (cert.getOrder().getName(), cert.getOrder().getContract()))

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
        exceptions = []
        for bundle in uep.getCertificatesBySerial(serials):
            try:
                key, cert = self.build(bundle)
                br.write(key, cert)
                report.added.append(cert)
            except Exception, e:
                log.exception(e)
                log.error(
                    'Bundle not loaded:\n%s\n%s',
                    bundle,
                    e)
                exceptions.append(e)
        return exceptions

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
        return '%s.pem' % str(sn)


class UEP(UEPConnection):

    @classmethod
    def consumerId(cls):
        try:
            cid = ConsumerIdentity.read()
            return cid.getConsumerId()
        except Exception, e:
            log.error(e)
            raise Disconnected()

    def __init__(self):
        cert = ConsumerIdentity.certpath()
        key = ConsumerIdentity.keypath()
        UEPConnection.__init__(self, cert_file=cert, key_file=key)
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
            reply = UEPConnection.getCertificates(self, self.uuid,
                                                  serials=snList)
            for cert in reply:
                result.append(cert)
        return result


class Disconnected(Exception):
    pass


class Path:

    # Used during Anaconda install by the yum pidplugin to ensure we operate
    # beneath /mnt/sysimage/ instead of /.
    ROOT = '/'

    @classmethod
    def join(cls, a, b):
        path = os.path.join(a, b)
        return cls.abs(path)

    @classmethod
    def abs(cls, path):
        """ Append the ROOT path to the given path. """
        if os.path.isabs(path):
            return os.path.join(cls.ROOT, path[1:])
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
        for p, fn in self.listAll():
            path = self.abspath(fn)
            if Path.isdir(path):
                continue
            else:
                files.append((p, fn))
        return files

    def listdirs(self):
        dir = []
        for p, fn in self.listAll():
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

    def abspath(self, filename):
        """
        Return path for a filename relative to this directory.
        """
        # NOTE: self.path is already aware of the Path.ROOT setting, so we
        # can just join normally.
        return os.path.join(self.path, filename)

    def __str__(self):
        return self.path


class CertificateDirectory(Directory):

    KEY = 'key.pem'

    def __init__(self, path):
        Directory.__init__(self, path)
        self.create()

    def list(self):
        listing = []
        factory = self.Factory(self.certClass())
        for p, fn in Directory.list(self):
            if not fn.endswith('.pem') or fn == self.KEY:
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

    # date is datetime.datetime object
    def listExpiredOnDate(self, date):
        expired = []
	for c in self.list():
            if not c.validRange().hasDate(date):
                expired.append(c)
	return expired

    def listExpired(self):
        expired = []
        for c in self.list():
            if not c.valid():
                expired.append(c)
        return expired

    def find(self, sn):
        # TODO: could optimize to just load SERIAL.pem? Maybe not in all cases.
        for c in self.list():
            if c.serialNumber() == sn:
                return c
        return None

    def findAllByProduct(self, hash):
        certs = []
        for c in self.list():
            for p in c.getProducts():
                if p.getHash() == hash:
                    certs.append(c)
        return certs

    def findByProduct(self, hash):
        for c in self.list():
            for p in c.getProducts():
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
                    raise Exception('\n - '.join(bogus))
                certlist.append(cert)
            except Exception, e:
                log.exception(e)
                log.error(
                    'File: %s, not loaded\n%s',
                    path,
                    e)


class ProductDirectory(CertificateDirectory):

    PATH = cfg.get('rhsm', 'productCertDir')

    def __init__(self):
        CertificateDirectory.__init__(self, self.PATH)

    def certClass(self):
        return ProductCertificate


class EntitlementDirectory(CertificateDirectory):

    PATH = cfg.get('rhsm', 'entitlementCertDir')
    PRODUCT = 'product'

    @classmethod
    def keypath(cls):
        return Path.join(cls.PATH, cls.KEY)

    @classmethod
    def productpath(cls):
         return cls.PATH

    def __init__(self):
        CertificateDirectory.__init__(self, self.productpath())

    def certClass(self):
        return EntitlementCertificate


class ConsumerIdentity:

    PATH = cfg.get('rhsm', 'consumerCertDir')
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
        return (os.path.exists(cls.keypath()) and \
                 os.path.exists(cls.certpath()))

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
        import managerlib
        self.__mkdir()
        f = open(self.keypath(), 'w')
        f.write(self.key)
        f.close()
        os.chmod(self.keypath(), managerlib.ID_CERT_PERMS)
        f = open(self.certpath(), 'w')
        f.write(self.cert)
        f.close()
        os.chmod(self.certpath(), managerlib.ID_CERT_PERMS)

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
        return (len(self.added) + len(self.rogue) + len(self.expd))

    def write(self, s, title, certificates):
        indent = '  '
        s.append(title)
        if certificates:
            for c in certificates:
                p = c.getProduct()
                if not p:
                   p = c.getOrder()

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


class CertSorter(object):
    """
    Class used to sort all certificates in the given Entitlement and Product
    directories into status for a particular date.

    Certs will be sorted into: installed, entitled, installed + entitled,
    installed + unentitled, expired.

    The date can be used to examine the state this system will likely be in
    at some point in the future.
    """
    def __init__(self, product_dir, entitlement_dir, on_date=None):
        self.product_dir = product_dir
        self.entitlement_dir = entitlement_dir
        if not on_date:
            on_date = datetime.now()

        prod_certs = self.product_dir.list()
        ent_certs = self.entitlement_dir.list()

        # These are the sorted cert lists we'll be populating:

        # products installed but not entitled (at all, even expired)
        self.unentitled = []

        # expired entitlements on the given date
        self.expired = []

        # valid entitlements on the given date, includes both installed
        # products, and those that are not installed but we have an
        # entitlement for anyhow.
        self.valid = []

        log.debug("Sorting product and entitlement cert status on: %s" %
                on_date)

        entdict = {}
        for cert in ent_certs:
            eproducts = cert.getProducts()
            for product in eproducts:
                entdict[product.getHash()] = cert
                #{
                #        'valid': cert.valid(),
                #        'expires': formatDate(cert.validRange().end().isoformat()),
                #        'serial': cert.serialNumber(),
                #        'contract': cert.getOrder().getContract(),
                #        'account': cert.getOrder().getAccountNumber()
                #}

        # track a list of entitlement product IDs we encounter product certs for:
        ent_product_ids_seen = []
        for product in prod_certs :
            product_id = product.getProduct().getHash()
            ent_product_ids_seen.append(product_id)
            if entdict.has_key(product_id):
                ent_product_ids_seen.append(product_id)
                if entdict[product_id].valid(on_date=on_date):
                    log.debug("%s valid" % product_id)
                    self.valid.append(entdict[product_id])
                else:
                    log.debug("%s expired" % product_id)
                    self.expired.append(entdict[product_id])
            else:
                self.unentitled.append(product)

        for product_id in entdict:
            if product_id not in ent_product_ids_seen:
                if entdict[product_id].valid(on_date=on_date):
                    log.debug("%s uninstalled but valid" % product_id)
                    self.valid.append(entdict[product_id])
                else:
                    log.debug("%s uninstalled and expired" % product_id)
                    self.expired.append(entdict[product_id])

        #for cert in EntitlementDirectory().list():
        #    for product in cert.getProducts():
        #        if product.getHash() not in psnames:
        #            psname = product.getHash()
        #            data = (psname, _('Not Installed'),
        #                    str(entdict[psname]['expires']),
        #                    entdict[psname]['serial'], entdict[psname]['contract'],
        #                    entdict[psname]['account'])
        #            product_status.append(data)
        #return product_status





def find_last_compliant(ent_dir=None, product_dir=None):
    """
    Find the first datetime where an entitlement will be uncompliant.
    If there are currently unentitled products, then return the current
    datetime.
    """
    # TODO: should we be listing valid? does this work if everything is already out of compliance?
    # TODO: setting a member variable here that isn't used anywhere else, should keep this local unless needed
    # TODO: needs unit testing imo, probably could be moved to a standalone method for that purpose
    if not ent_dir:
        ent_dir = EntitlementDirectory()
    if not product_dir:
        product_dir = ProductDirectory()

    valid_ents = ent_dir.listValid()

    installed_not_entitled = []
    for product_cert in product_dir.list():
        if not ent_dir.findByProduct(product_cert.getProduct().getHash()):
            installed_not_entitled.append(product_cert)

    def get_date(ent_cert):
        return ent_cert.validRange().end()

    valid_ents.sort(key=get_date)

    # next cert to go noncompliant
    if valid_ents and not installed_not_entitled:
        return valid_ents[0].validRange().end()
    else:
        return datetime.now(GMT())





def main():
    print _('Updating Red Hat certificates')
    certlib = CertLib()
    updates = certlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()

