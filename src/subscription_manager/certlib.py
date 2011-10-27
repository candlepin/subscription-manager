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
from subscription_manager.lock import Lock
from subscription_manager import cert_sorter
from subscription_manager.certdirectory import EntitlementDirectory, \
    ProductDirectory, Path, Writer
from subscription_manager import constants
from rhsm.config import initConfig
from rhsm.certificate import *

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


class DataLib:

    def __init__(self, lock=ActionLock(), uep=None):
        self.lock = lock
        self.uep = uep

    def update(self):
        lock = self.lock
        lock.acquire()
        try:
            return self._do_update()
        finally:
            lock.release()

    def _do_update(self):
        return


class CertLib(DataLib):

    def __init__(self, lock=ActionLock(), uep=None):
        DataLib.__init__(self, lock, uep)

    def delete(self, serialNumbers):
        lock = self.lock
        lock.acquire()
        try:
            return self._do_delete(serialNumbers)
        finally:
            lock.release()

    def _do_update(self):
        action = UpdateAction(uep=self.uep)
        return action.perform()

    def _do_delete(self, serialNumbers):
        action = DeleteAction()
        return action.perform(serialNumbers)


class HealingLib(DataLib):
    """
    An object used to run healing nightly. Checks compliance for today, heals
    if necessary, then checks for 24 hours from now, so we theoretically will
    never go out of compliance if subscriptions are available.
    """

    def __init__(self, lock=ActionLock(), uep=None, facts_dict=None):
        self.facts_dict = facts_dict
        DataLib.__init__(self, lock, uep)

    def _do_update(self):
        uuid = ConsumerIdentity.read().getConsumerId()
        consumer = self.uep.getConsumer(uuid)
        from subscription_manager import managerlib

        if 'autoheal' in consumer and consumer['autoheal']:
            try:
                log.info("Checking if system requires healing.")

                today = datetime.now(GMT())
                tomorrow = today + timedelta(days=1)

                prod_dir = ProductDirectory()

                # Check if we're out of compliance today and heal if so. If not
                # we'll do the same check for tomorrow to hopefully always keep
                # us compliant:
                ent_dir = EntitlementDirectory()
                cs = cert_sorter.CertSorter(prod_dir, ent_dir,
                        on_date=today)
                cert_updater = CertLib(uep=self.uep)
                if not cs.is_valid():
                    log.warn("Found invalid entitlements for today: %s" %
                            today)
                    self.uep.bind(uuid, today)
                    cert_updater.update()
                else:
                    log.info("Entitlements are valid for today: %s" %
                            today)

                    cs = cert_sorter.CertSorter(prod_dir, ent_dir,
                            on_date=tomorrow)
                    if not cs.is_valid():
                        log.warn("Found invalid entitlements for tomorrow: %s" %
                                tomorrow)
                        self.uep.bind(uuid, tomorrow)
                        cert_updater.update()
                    else:
                        log.info("Entitlements are valid for tomorrow: %s" %
                                tomorrow)

            except Exception, e:
                log.error("Error attempting to auto-heal:")
                log.exception(e)
                return 0
            else:
                log.info("Auto-heal check complete.")
                #FIXME: this may need to be changed with getInstalledProductStatus
                # changes
                installed_status = managerlib.getInstalledProductStatus()
                log.info("Current installed product status:")
                for prod_status in installed_status:
                    log.info(constants.product_status % (prod_status[0],
                        prod_status[1]))
                return 1
        else:
            log.info("Auto-heal disabled on server, skipping.")
            return 0


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
        # WARNING: TODO: XXX: this is returning a tuple, the parent class and
        # all other sub-classes return an int, which somewhat defeats
        # the purpose...
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
        for valid in self.entdir.list():
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


class Disconnected(Exception):
    pass


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


def find_first_invalid_date(ent_dir=None, product_dir=None):
    """
    Find the first date when the system is out of compliance at midnight
    GMT.

    WARNING: This method does *not* return the exact first datetime when
    we're out of compliance. Due to it's uses in the GUI it needs to
    return a datetime into the first day of complete non-compliance so
    the subscription assistant can search for that time and find expired
    products.

    If there are no products installed, return None, as there technically
    is no first invalid date.
    """
    if not ent_dir:
        ent_dir = EntitlementDirectory()
    if not product_dir:
        product_dir = ProductDirectory()

    current_date = datetime.now(GMT())

    if not product_dir.list():
        # If there are no products installed, return None, there is no
        # invalid date:
        log.debug("Unable to determine first invalid date, no products "
                "installed.")
        return None

    # change _scan_entitlement_certs to take product lists,
    # run it for the future to figure this out
    # First check if we have anything installed but not entitled *today*:
    cs = cert_sorter.CertSorter(product_dir, ent_dir, on_date=current_date)
    # TODO: partially stacked?
    if cs.unentitled_products or cs.expired_products:
        log.debug("Found installed but not entitled products.")
        return current_date

    # Sort all the ent certs by end date. (ascending)
    all_ent_certs = ent_dir.list()

    def get_date(ent_cert):
        return ent_cert.validRange().end()

    all_ent_certs.sort(key=get_date)

    # Loop through all current and future entitlement certs, check compliance
    # status on their end date, and return the first date where we're not
    # compliant.
    for ent_cert in all_ent_certs:
        # Adding a timedelta of one day here so we can be sure we get a date
        # the subscription assitant (which does not use time) can use to search
        # for.
        end_date = ent_cert.validRange().end() + timedelta(days=1)
        if end_date < current_date:
            # This cert is expired, ignore it:
            continue
        log.debug("Checking cert: %s, end date: %s" % (ent_cert.serialNumber(),
            end_date))

        # new cert_sort stuff, use _scan_for_entitled_products, since
        # we just need to know if stuff is expired
        cs = cert_sorter.CertSorter(product_dir, ent_dir, on_date=end_date)
        # TODO: partially stacked?
        if cs.expired_products:
            log.debug("Found non-compliant status on %s" % end_date)
            return end_date
        else:
            log.debug("Compliant on %s" % end_date)

    # Should never hit this:
    raise Exception("Unable to determine first invalid date.")


def main():
    print _('Updating entitlement certificates')
    certlib = CertLib()
    updates = certlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()
