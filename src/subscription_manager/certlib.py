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
from rhsm.config import initConfig
from rhsm.certificate import Key, create_from_pem, GMT

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


class DataLib(object):

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
    An object used to run healing nightly. Checks cert validity for today, heals
    if necessary, then checks for 24 hours from now, so we theoretically will
    never have invalid certificats if subscriptions are available.
    """

    def __init__(self, lock=ActionLock(), uep=None, facts_dict=None,
                 product_dir=None):
        self.facts_dict = facts_dict
        DataLib.__init__(self, lock, uep)

        self._product_dir = product_dir or ProductDirectory()

    def _do_update(self):
        uuid = ConsumerIdentity.read().getConsumerId()
        consumer = self.uep.getConsumer(uuid)

        if 'autoheal' in consumer and consumer['autoheal']:
            try:
                log.info("Checking if system requires healing.")

                today = datetime.now(GMT())
                tomorrow = today + timedelta(days=1)

                # Check if we're not valid today and heal if so. If not
                # we'll do the same check for tomorrow to hopefully always keep
                # us valid:
                ent_dir = EntitlementDirectory()
                cs = cert_sorter.CertSorter(self._product_dir, ent_dir,
                        self.facts_dict, on_date=today)
                cert_updater = CertLib(lock=self.lock, uep=self.uep)
                if not cs.is_valid():
                    log.warn("Found invalid entitlements for today: %s" %
                            today)
                    self.uep.bind(uuid, today)
                    cert_updater.update()
                else:
                    log.info("Entitlements are valid for today: %s" %
                            today)

                    cs = cert_sorter.CertSorter(self._product_dir, ent_dir,
                            self.facts_dict, on_date=tomorrow)
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
                return 1
        else:
            log.info("Auto-heal disabled on server, skipping.")
            return 0


class IdentityCertLib(DataLib):
    """
    An object to update the identity certificate in the event the server
    deems it is about to expire. This is done to prevent the identity
    certificate from expiring thus disallowing connection to the server
    for updates.
    """

    def __init__(self, lock=ActionLock(), uep=None):
        super(IdentityCertLib, self).__init__(lock, uep)

    def _do_update(self):
        if not ConsumerIdentity.existsAndValid():
            # we could in theory try to update the id in the
            # case of it being bogus/corrupted, ala #844069,
            # but that seems unneeded
            return 0

        from subscription_manager import managerlib

        idcert = ConsumerIdentity.read()
        uuid = idcert.getConsumerId()
        consumer = self.uep.getConsumer(uuid)
        # only write the cert if the serial has changed
        if idcert.getSerialNumber() != consumer['idCert']['serial']['serial']:
            log.debug('identity certificate changed, writing new one')
            managerlib.persist_consumer_cert(consumer)
        return 1


class Action:

    def __init__(self, uep=None):
        self.entdir = EntitlementDirectory()
        self.uep = uep

    def build(self, bundle):
        keypem = bundle['key']
        crtpem = bundle['cert']
        key = Key(keypem)

        cert = create_from_pem(crtpem)
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
                (cert.order.name, cert.order.contract))
            for product in cert.products:
                system_log("Added subscription for product '%s'" % \
                    (product.name))
        for cert in report.rogue:
            system_log("Removed subscription for '%s' contract '%s'" % \
                (cert.order.name, cert.order.contract))
            for product in cert.products:
                system_log("Removed subscription for product '%s'" % \
                    (product.name))
        for cert in report.expired:
            system_log("Expired subscription for '%s' contract '%s'" % \
                (cert.order.name, cert.order.contract))
            for product in cert.products:
                system_log("Expired subscription for product '%s'" % \
                    (product.name))

    def getLocal(self, report):
        local = {}
        #certificates in grace period were being renamed everytime.
        #this makes sure we don't try to re-write certificates in
        #grace period
        # XXX since we don't use grace period, this might not be needed
        for valid in self.entdir.list():
            sn = valid.serial
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
        # if there is no UEP object, short circuit
        if self.uep is None:
            return results
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
            report.expired.append(cert)
            cert.delete()


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
        if cls.exists():
            try:
                cls.read()
                return True
            except Exception, e:
                log.warn('possible certificate corruption')
                log.error(e)
        return False

    def __init__(self, keystring, certstring):
        self.key = keystring
        # TODO: bad variables, cert should be the certificate object, x509 is
        # used elsewhere for the m2crypto object of the same name.
        self.cert = certstring
        self.x509 = create_from_pem(certstring)

    def getConsumerId(self):
        subject = self.x509.subject
        return subject.get('CN')

    def getConsumerName(self):
        altName = self.x509.alt_name
        return altName.replace("DirName:/CN=", "")

    def getSerialNumber(self):
        return self.x509.serial

    # TODO: we're using a Certificate which has it's own write/delete, no idea
    # why this landed in a parallel disjoint class wrapping the actual cert.
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
        self.expired = []

    def updates(self):
        return (len(self.added) + len(self.rogue) + len(self.expired))

    def write(self, s, title, certificates):
        indent = '  '
        s.append(title)
        if certificates:
            for c in certificates:
                products = c.products
                if not products:
                    product = c.order
                for product in products:
                    s.append('%s[sn:%d (%s,) @ %s]' % \
                        (indent,
                         c.serial,
                         product.name,
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
        self.write(s, _('Expired (deleted):'), self.expired)
        return '\n'.join(s)


def main():
    print _('Updating entitlement certificates')
    certlib = CertLib()
    updates = certlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()
