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
import syslog
import logging
from datetime import timedelta, datetime
from rhsm.connection import UEPConnection
from rhsm.certificate import *
from subscription_manager.lock import Lock
from rhsm.config import initConfig


log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = gettext.gettext

cfg = initConfig()


def system_log(message, priority=syslog.LOG_NOTICE):
	syslog.openlog("subscription-manager")
	syslog.syslog(priority, message)

class ActionLock(Lock):

    PATH = '/var/run/rhsm/cert.pid'

    def __init__(self):
        Lock.__init__(self, self.PATH)


class CertLib:

    def __init__(self, lock=ActionLock(), uep=None):
        self.lock = lock
        self.uep = uep

    def update(self):
        lock = self.lock
        lock.acquire()
        try:
            action = UpdateAction(uep=self.uep)
            return action.perform()
        finally:
            lock.release()

    def delete(self, serialNumbers):
        lock = self.lock
        lock.acquire()
        try:
            action = DeleteAction()
            return action.perform(serialNumbers)
        finally:
            lock.release()


class Action:

    def __init__(self, uep=None):
        self.entdir = EntitlementDirectory()
        self.uep = uep

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




class DeleteAction(Action):

    def perform(self, serialNumbers):
        for sn in serialNumbers:
            cert = self.entdir.find(sn)
            if cert is None:
                continue
            cert.delete()
        return self


class UpdateAction(Action):

    def perform(self):
        report = UpdateReport()
        local = self.getLocal(report)
        expected = self.getExpected(report)
        missing, rogue = self.bashSerials(local, expected, report)
        self.delete(rogue, report)
        exceptions = self.install(missing, report)
        self.purgeExpired(report)
        log.info('certs updated:\n%s', report)
        self.syslogResults(report)
        return (report.updates(), exceptions)

    def syslogResults(self, report):
        for cert in report.added:
            system_log("Added subscription for '%s' contract '%s'" % \
                (cert.getOrder().getName(), cert.getOrder().getContract()))
            for product in cert.getProducts():
                system_log("Added subscription for product '%s'" % \
                    (product.getName()))
        for cert in report.rogue:
            system_log("Removed subscription for '%s' contract '%s'" % \
                (cert.getOrder().getName(), cert.getOrder().getContract()))
            for product in cert.getProducts():
                system_log("Removed subscription for product '%s'" % \
                    (product.getName()))
        for cert in report.expnd:
            system_log("Expired subscription for '%s' contract '%s'" % \
                (cert.getOrder().getName(), cert.getOrder().getContract()))
            for product in cert.getProducts():
                system_log("Expired subscription for product '%s'" % \
                    (product.getName()))

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

    def _getConsumerId(self):
        try:
            cid = ConsumerIdentity.read()
            return cid.getConsumerId()
        except Exception, e:
            log.error(e)
            raise Disconnected()

    def getCertificateSerialsList(self):
        results = []
        reply = self.uep.getCertificateSerials(self._getConsumerId())
        for d in reply:
            sn = d['serial']
            results.append(sn)
        return results

    def getExpected(self, report):
        exp = self.getCertificateSerialsList()
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

    def getCertificatesBySerialList(self, snList):
        result = []
        if snList:
            snList = [str(sn) for sn in snList]
            reply = self.uep.getCertificates(self._getConsumerId(),
                                              serials=snList)
            for cert in reply:
                result.append(cert)
        return result

    def install(self, serials, report):
        br = Writer()
        exceptions = []
        for bundle in self.getCertificatesBySerialList(serials):
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
        serial = cert.serialNumber()
        ent_dir_path = self.entdir.productpath()

        key_filename = '%s-key.pem' % str(serial)
        key_path = Path.join(ent_dir_path, key_filename)
        key.write(key_path)

        cert_filename = '%s.pem' % str(serial)
        cert_path = Path.join(ent_dir_path, cert_filename)
        cert.write(cert_path)


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
            if not fn.endswith('.pem') or fn.endswith(self.KEY):
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

    def get_provided_tags(self):
        """
        Iterates all product certificates in the directory and extracts a master
        set of all tags they provide.
        """
        tags = set()
        for prod_cert in self.listValid():
            for product in prod_cert.getProducts():
                for tag in product.getProvidedTags():
                    tags.add(tag)
        return tags


class EntitlementDirectory(CertificateDirectory):

    PATH = cfg.get('rhsm', 'entitlementCertDir')
    PRODUCT = 'product'

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
        from subscription_manager import managerlib
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
                products = c.getProducts()
                if not products:
                   product = c.getOrder()
                   
                for product in products:
                    s.append('%s[sn:%d (%s,) @ %s]' % \
                        (indent,
                         c.serialNumber(),
                         product.getName(),
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

    When looking for the products we need, only installed products will be
    considered. (i.e. we do not concern ourselves with products that are
    entitled but not installed)

    The date can be used to examine the state this system will likely be in
    at some point in the future.
    """
    def __init__(self, product_dir, entitlement_dir, on_date=None):
        self.product_dir = product_dir
        self.entitlement_dir = entitlement_dir
        if not on_date:
            on_date = datetime.now()
        self.on_date = on_date

        self.expired_entitlement_certs = []
        self.valid_entitlement_certs = []

        # All products installed on this machine, regardless of status. Maps
        # product ID to certlib.Product object.
        self.all_products = {}

        # the specific products that are not entitled in the above certs,
        # dict maps product ID to product certificate.
        self.unentitled_products = {}

        # specific products which are installed, we're entitled, but have expired
        # on the date in question. this must watch out for possibility some other
        # entitlement certificate provides this product. Certificates which are
        # within their grace period will appear in this dict. maps product ID
        # to the expired entitlement certificate:
        self.expired_products = {}

        # specific products which are installed, and entitled on the given date.
        # maps product ID to the valid entitlement certificate:
        self.valid_products = {}

        log.debug("Sorting product and entitlement cert status for: %s" %
                on_date)

        self._populate_all_products()

        self._scan_entitlement_certs()

        self._scan_for_unentitled_products()

        self._remove_expired_if_valid_elsewhere()
        log.debug("valid entitled products: %s" % self.valid_products.keys())
        log.debug("expired entitled products: %s" % self.expired_products.keys())

    def _populate_all_products(self):
        """ Build the dict of all installed products. """
        prod_certs = self.product_dir.list()
        for product_cert in prod_certs:
            product = product_cert.getProduct()
            self.all_products[product.getHash()] = product_cert
        log.debug("Installed product IDs: %s" % self.all_products.keys())

    def _scan_entitlement_certs(self):
        ent_certs = self.entitlement_dir.list()

        for ent_cert in ent_certs:

            if ent_cert.valid(on_date=self.on_date):
                self.valid_entitlement_certs.append(ent_cert)

                self._scan_ent_cert_products(ent_cert, self.valid_products)
            else:
                self.expired_entitlement_certs.append(ent_cert)
                log.debug("expired:")
                log.debug(ent_cert.getProduct().getHash())
                self._scan_ent_cert_products(ent_cert, self.expired_products)

    def _scan_ent_cert_products(self, ent_cert, product_dict):
        """
        Scans this ent certs products, checks if they are installed, and
        adds them to the provided dict (expired/valid) if so:
        """
        for product in ent_cert.getProducts():
            product_id = product.getHash()
            # Is this an installed product?
            if product_id in self.all_products:
                product_dict[product_id] = ent_cert

    def _scan_for_unentitled_products(self):
        # For all installed products, if not in valid or expired hash, it
        # must be completely unentitled
        for product_id in self.all_products.keys():
            if (not product_id in self.valid_products) and \
                (not product_id in self.expired_products):
                    self.unentitled_products[product_id] = \
                            self.all_products[product_id]

    def _remove_expired_if_valid_elsewhere(self):
        """
        Scan the expired products, if any are showing up also in the valid dict,
        remove them from expired.

        This catches situations where an entitlement for a product expires, but
        another still valid entitlement already provides the missing product.
        """
        for product_id in self.expired_products.keys():
            if product_id in self.valid_products:
                del self.expired_products[product_id]


def find_first_invalid_date(ent_dir=None, product_dir=None):
    """
    Find the first datetime where an entitlement will be invalid.
    If there are currently unentitled products, then return the current
    datetime.
    """
    # TODO: should we be listing valid? does this work if everything is already invalid?
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

    # next cert to go invalid
    if valid_ents and not installed_not_entitled:
        # Add a day, we don't want a date where we're still valid:
        last_cert = valid_ents[0].validRange().end()
        td = timedelta(days=1)
        return last_cert + td
    else:
        return datetime.now(GMT())





def main():
    print _('Updating entitlement certificates')
    certlib = CertLib()
    updates = certlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()

