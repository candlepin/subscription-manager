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

from datetime import datetime, timedelta
import gettext
import logging
import socket
import syslog

from rhsm.config import initConfig
from rhsm.certificate import Key, create_from_pem, GMT

from subscription_manager.certdirectory import Writer
from subscription_manager import rhelentbranding
from subscription_manager.identity import ConsumerIdentity
from subscription_manager.injection import CERT_SORTER, PLUGIN_MANAGER, IDENTITY, require
import subscription_manager.injection as inj
from subscription_manager.lock import Lock

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext

cfg = initConfig()


def system_log(message, priority=syslog.LOG_NOTICE):
    syslog.openlog("subscription-manager")
    syslog.syslog(priority, message.encode("utf-8"))


class ActionLock(Lock):

    PATH = '/var/run/rhsm/cert.pid'

    def __init__(self):
        Lock.__init__(self, self.PATH)

# TODO: *Lib objects should probably all support a Report object
#        ala CertLib, even if most of them would be simple or
#        or noops. Would make logging easier and more useful
#        and reduce some of the random variations in *Lib
class DataLib(object):

    def __init__(self, lock=None, uep=None):
        self.lock = lock

        # Need to do this here rather than with a default argument to prevent
        # circular dependency problems:
        if not self.lock:
            self.lock = ActionLock()

        self.uep = uep

    def update(self):
        self.lock.acquire()
        try:
            return self._do_update()
        finally:
            self.lock.release()

    def _do_update(self):
        return


class CertLib(DataLib):

    def __init__(self, lock=ActionLock(), uep=None):
        DataLib.__init__(self, lock, uep)
        self.report = UpdateReport()

    def delete(self, serial_numbers):
        lock = self.lock
        lock.acquire()
        try:
            return self._do_delete(serial_numbers)
        finally:
            lock.release()

    def _do_update(self):
        action = UpdateAction(uep=self.uep, report=self.report)
        return action.perform()

    def _do_delete(self, serial_numbers):
        action = DeleteAction()
        return action.perform(serial_numbers)


class HealingLib(DataLib):
    """
    An object used to run healing nightly. Checks cert validity for today, heals
    if necessary, then checks for 24 hours from now, so we theoretically will
    never have invalid certificats if subscriptions are available.
    """

    def __init__(self, lock=ActionLock(), uep=None, product_dir=None):
        DataLib.__init__(self, lock, uep)

        self._product_dir = product_dir or inj.require(inj.PROD_DIR)
        self.plugin_manager = require(PLUGIN_MANAGER)

    def _do_update(self):
        uuid = ConsumerIdentity.read().getConsumerId()
        consumer = self.uep.getConsumer(uuid)

        if 'autoheal' in consumer and consumer['autoheal']:
            try:
                log.info("Checking if system requires healing.")

                today = datetime.now(GMT())
                tomorrow = today + timedelta(days=1)

                # Check if we're invalid today and heal if so. If we are
                # valid, see if 24h from now is greater than our "valid until"
                # date, and heal for tomorrow if so.

                cs = require(CERT_SORTER)
                cert_updater = CertLib(lock=self.lock, uep=self.uep)
                if not cs.is_valid():
                    log.warn("Found invalid entitlements for today: %s" %
                            today)
                    self.plugin_manager.run("pre_auto_attach", consumer_uuid=uuid)
                    ents = self.uep.bind(uuid, today)
                    self.plugin_manager.run("post_auto_attach", consumer_uuid=uuid,
                                            entitlement_data=ents)
                    cert_updater.update()
                else:
                    log.info("Entitlements are valid for today: %s" %
                            today)

                    if cs.compliant_until is None:
                        # Edge case here, not even sure this can happen as we
                        # should have a compliant until date if we're valid
                        # today, but just in case:
                        log.warn("Got valid status from server but no valid until date.")
                    elif tomorrow > cs.compliant_until:
                        log.warn("Entitlements will be invalid by tomorrow: %s" %
                                tomorrow)
                        self.plugin_manager.run("pre_auto_attach", consumer_uuid=uuid)
                        ents = self.uep.bind(uuid, tomorrow)
                        self.plugin_manager.run("post_auto_attach", consumer_uuid=uuid,
                                                entitlement_data=ents)
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

    def __init__(self, uep=None, entdir=None):
        self.entdir = entdir or inj.require(inj.ENT_DIR)
        self.uep = uep


# TODO: rename to EntitlementCertDeleteAction
class DeleteAction(Action):

    def perform(self, serial_numbers):
        for sn in serial_numbers:
            cert = self.entdir.find(sn)
            if cert is None:
                continue
            cert.delete()
        return self


# TODO: rename to EntitlementCertUpdateAction
class UpdateAction(Action):

    def __init__(self, uep=None, entdir=None, report=None):
        Action.__init__(self, uep=uep, entdir=entdir)
        self.identity = require(IDENTITY)
        self.report = report

    # NOTE: this is slightly at odds with the manual cert import
    #       path, manual import certs wont get a 'report', etc
    def perform(self):
        local = self._get_local_serials(self.report)
        try:
            expected = self._get_expected_serials(self.report)
        except socket.error, ex:
            log.exception(ex)
            log.error('Cannot modify subscriptions while disconnected')
            raise Disconnected()

        missing_serials = self._find_missing_serials(local, expected)
        rogue_serials = self._find_rogue_serials(local, expected)

        self.delete(rogue_serials, self.report)
        self.install(missing_serials, self.report)

        log.info('certs updated:\n%s', self.report)
        self.syslog_results(self.report)

        if missing_serials or rogue_serials:
            # refresh yum repo's now
            self.repo_hook(lock=lock)

            # NOTE: Since we have the yum repos defined here now
            #       we could update product id certs here, or install
            #       them if they are needed, but missing. That way the
            #       branding installs could be more accurate.

            # reload certs and update branding
            self.branding_hook()

        # if we want the full report, we can get it, but
        # this makes CertLib.update() have same sig as reset
        # of *Lib.update
        return self.report.updates()

    def install(self, missing_serials, report):

        cert_bundles = self.get_certificates_by_serial_list(missing_serials)

        ent_cert_bundles_installer = EntitlementCertBundlesInstaller(report)
        ent_cert_bundles_installer.install(cert_bundles)
        self.report = ent_cert_bundles_installer.report
        self.exceptions = ent_cert_bundles_installer.exceptions

    def _find_missing_serials(self, local, expected):
        """ Find serials from the server we do not have locally. """
        missing = [sn for sn in expected if sn not in local]
        return missing

    def _find_rogue_serials(self, local, expected):
        """ Find serials we have locally but are not on the server. """
        rogue = [local[sn] for sn in local if not sn in expected]
        return rogue

    def syslog_results(self, report):
        for cert in report.added:
            system_log("Added subscription for '%s' contract '%s'" %
                       (cert.order.name, cert.order.contract))
            for product in cert.products:
                system_log("Added subscription for product '%s'" %
                           (product.name))
        for cert in report.rogue:
            system_log("Removed subscription for '%s' contract '%s'" %
                       (cert.order.name, cert.order.contract))
            for product in cert.products:
                system_log("Removed subscription for product '%s'" %
                           (product.name))

    def _get_local_serials(self, report):
        local = {}
        #certificates in grace period were being renamed everytime.
        #this makes sure we don't try to re-write certificates in
        #grace period
        # XXX since we don't use grace period, this might not be needed
        self.entdir.refresh()
        for valid in self.entdir.list():
            sn = valid.serial
            report.valid.append(sn)
            local[sn] = valid
        return local

    def _get_consumer_id(self):
        try:
            cid = ConsumerIdentity.read()
            return cid.getConsumerId()
        except Exception, e:
            log.error(e)
            raise Disconnected()

    def get_certificate_serials_list(self):
        results = []
        # if there is no UEP object, short circuit
        if self.uep is None:
            return results
        reply = self.uep.getCertificateSerials(self._get_consumer_id())
        for d in reply:
            sn = d['serial']
            results.append(sn)
        return results

    def get_certificates_by_serial_list(self, sn_list):
        """Fetch a list of entitlement certificates specified by a list of serial numbers"""
        result = []
        if sn_list:
            sn_list = [str(sn) for sn in sn_list]
            # NOTE: use injected IDENTITY, need to validate this
            # handles disconnected errors properly
            reply = self.uep.getCertificates(self.identity.getConsumerId(),
                                              serials=sn_list)
            for cert in reply:
                result.append(cert)
        return result

    def _get_expected_serials(self, report):
        exp = self.get_certificate_serials_list()
        report.expected = exp
        return exp

    def delete(self, rogue, report):
        for cert in rogue:
            try:
                cert.delete()
                report.rogue.append(cert)
            except OSError, er:
                log.exception(er)
                log.warn("Failed to delete cert")

        # If we just deleted certs, we need to refresh the now stale
        # entitlement directory before we go to delete expired certs.
        rogue_count = len(report.rogue)
        if rogue_count > 0:
            print gettext.ngettext("%s local certificate has been deleted.",
                                   "%s local certificates have been deleted.",
                                   rogue_count) % rogue_count
            self.entdir.refresh()


class EntitlementCertBundlesInstaller(object):
    """Install a list of entitlement cert bundles"""

    def __init__(self, report):
        self.exceptions = []
        self.report = report

    def install(self, cert_bundles):
        """Fetch entitliement certs, install them, and update the report"""
        bundle_installer = EntitlementCertBundleInstaller()
        for cert_bundle in cert_bundles:
            bundle_installer.install(cert_bundle, self.report)
        self.exceptions = bundle_installer.exceptions
        self.post_install()

    # pre and post
    def post_install(self):
        """after all cert bundles have been installed"""
        for installed in self._get_installed():
            print "installed! list", installed

    def get_installed(self):
        return self._get_installed()


    def repo_hook(self, lock):
        """Update yum repos

        Args:
            lock: an ActionLock, in this case certlib.UpdateAction lock, since repo_kook
                  is called when UpdateAction has already acquired a lock.
        """
        try:
            # repolib/RepoLib imports certlib, so import late until
            #  we factor out our circular deps
            from subscription_manager.repolib import RepoLib
            rl = RepoLib(lock=lock, uep=self.uep)
            rl.update()
        except Exception, e:
            log.debug(e)
            log.debug("Failed to update repos")

    def branding_hook(self):
        """Update branding info based on entitlement cert changes"""

        # RHELBrandsInstaller will use latest ent_dir contents
        brands_installer = rhelentbranding.RHELBrandsInstaller()
        brands_installer.install()

    def install(self, serials, report):
        br = Writer()
        exceptions = []
        for bundle in self.get_certificates_by_serial_list(serials):
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
        for bundle in self.get_certificates_by_serial_list(serials):
            self.install_cert_bundle(bundle, report)

    # we have a UpdateReport, use it
    def _get_installed(self):
        return self.report.added



class EntitlementCertBundleInstaller(object):

    def __init__(self):
        self.exceptions = []

    def pre_install(self, bundle):
        print "Ecbi.pre_install", bundle

    def install(self, bundle, report):
        self.pre_install(bundle)

        cert_bundle_writer = Writer()
        try:
            key, cert = self.build_cert(bundle)
            cert_bundle_writer.write(key, cert)

            report.added.append(cert)
        except Exception, e:
            self.install_exception(bundle, e)

        self.post_install(bundle)

    def install_exception(self, bundle, exception):
        log.exception(exception)
        log.error('Bundle not loaded:\n%s\n%s', bundle, exception)

        # FIXME: pick one
        self.exceptions.append(exception)
        self.report.exceptions.append(exception)

    def post_install(self, bundle):

        print "Ecbi.post_install"

    # should probably be in python-rhsm/certificate
    def build_cert(self, bundle):
        keypem = bundle['key']
        crtpem = bundle['cert']

        key = Key(keypem)
        cert = create_from_pem(crtpem)

        return (key, cert)


class Disconnected(Exception):
    pass


class UpdateReport:

    def __init__(self):
        self.valid = []
        self.expected = []
        self.added = []
        self.rogue = []
        self.exceptions = []

    def updates(self):
        return (len(self.added) + len(self.rogue))

    def write(self, s, title, certificates):
        indent = '  '
        s.append(title)
        if certificates:
            for c in certificates:
                products = c.products
                if not products:
                    s.append('%s[sn:%d (%s) @ %s]' %
                             (indent,
                              c.serial,
                              c.order.name,
                              c.path))
                for product in products:
                    s.append('%s[sn:%d (%s,) @ %s]' %
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
        return '\n'.join(s)


def main():
    print _('Updating entitlement certificates')
    certlib = CertLib()
    updates = certlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()
