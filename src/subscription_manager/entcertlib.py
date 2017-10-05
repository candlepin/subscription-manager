from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2014 Red Hat, Inc.
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
import logging
import socket

from rhsm.certificate import Key, create_from_pem
from rhsm.certificate2 import CONTENT_ACCESS_CERT_TYPE

from subscription_manager.certdirectory import Writer
from subscription_manager import certlib
from subscription_manager import content_action_client
from subscription_manager import utils
from subscription_manager.injection import IDENTITY, require
from subscription_manager import rhelentbranding
import subscription_manager.injection as inj

from subscription_manager.i18n import ungettext, ugettext as _

log = logging.getLogger(__name__)

CONTENT_ACCESS_CERT_CAPABILITY = "org_level_content_access"


class EntCertActionInvoker(certlib.BaseActionInvoker):
    """Invoker for entitlement certificate updating actions."""
    def _do_update(self):
        action = EntCertUpdateAction()
        return action.perform()


# this guy is an oddball
# NOTE: this lib and EntCertDeleteAction are currently
# unused. Intention is to replace managerlib.clean_all_data
# with a CertActionClient.delete invocation
class EntCertDeleteLib(object):
    """Invoker for entitlement certificate delete actions."""
    def __init__(self, serial_numbers=None,
                ent_dir=None):
        self.locker = certlib.Locker()
        self.ent_dir = ent_dir

    def delete(self):
        self.locker.run(self._do_delete)

    def _do_delete(self):
        action = EntCertDeleteAction(ent_dir=self.ent_dir,
                                    serial_numbers=self.serial_numbers)
        return action.perform()


# FIXME: currently unused
class EntCertDeleteAction(object):
    """Action for deleting all entitlement certs."""
    def __init__(self, ent_dir=None):
        self.ent_dir = ent_dir

    def perform(self, serial_numbers):
        for sn in serial_numbers:
            cert = self.ent_dir.find(sn)
            if cert is None:
                continue
            cert.delete()
        return self


class EntCertUpdateAction(object):
    """Action for syncing entitlement certificates.

    EntCertUpdateAction is used to sync entitlement certs based on
    currently entitlement status.

    An EntCertUpdateReport is returned containing information about the changes
    that were applied. install() and delete() methods are expected to update
    self.report.

    New and updated ent certs are installed via a EntitlementCertBundlesInstaller.
    Expired or extraneous entitlement certs are deleted.

    If there are changes applied to the EntitltementDirectory, repo_hook()
    and branding_hook() are triggered. Certificates will have been updated,
    and written to disk, and EntitlementDirectory refresh before these hooks
    are called.

    The injected self.uep is used to query RHSM API for a list of expected
    entitlement certificate serial numbers. If local system is missing certs
    matching those serial numbers, the API is queried for the list of serial
    numbers to update.

    rogue: ent certs installed on system but not known by RHSM API.
    missing: ent certs RHSM API knows, but are not installed on system.
    """
    def __init__(self, report=None):
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = self.cp_provider.get_consumer_auth_cp()
        self.ent_dir = inj.require(inj.ENT_DIR)
        self.identity = require(IDENTITY)
        self.report = EntCertUpdateReport()
        self.content_access_cache = inj.require(inj.CONTENT_ACCESS_CACHE)

    # NOTE: this is slightly at odds with the manual cert import
    #       path, manual import certs wont get a 'report', etc
    def perform(self):
        local = self._get_local_serials()
        try:
            expected = self._get_expected_serials()
        except socket.error as ex:
            log.exception(ex)
            log.error('Cannot modify subscriptions while disconnected')
            raise Disconnected()

        missing_serials = self._find_missing_serials(local, expected)
        rogue_serials = self._find_rogue_serials(local, expected)

        self.delete(rogue_serials)
        self.install(missing_serials)

        log.info('certs updated:\n%s', self.report)
        self.syslog_results()

        if missing_serials or rogue_serials:

            # We call EntCertlibActionInvoker.update() solo from
            # the 'attach' cli instead of an ActionClient. So
            # we need to refresh the ent_dir object before calling
            # content updating actions.
            self.ent_dir.refresh()
            self.content_access_hook()
            self.repo_hook()

            # NOTE: Since we have the yum repos defined here now
            #       we could update product id certs here, or install
            #       them if they are needed, but missing. That way the
            #       branding installs could be more accurate.

            # reload certs and update branding
            self.branding_hook()

        if self.uep.has_capability(CONTENT_ACCESS_CERT_CAPABILITY):
            content_access_certs = self._find_content_access_certs()
            update_data = None
            if len(content_access_certs) > 0:
                # This address BZ: 1448855, 1450862
                if len(expected) < len(content_access_certs):
                    obsolete_certs = []
                    for cont_access_cert in content_access_certs:
                        if cont_access_cert.serial not in expected:
                            obsolete_certs.append(cont_access_cert)
                    log.info('Deleting obsolete content access certificate')
                    self.delete(obsolete_certs)
                update_data = self.content_access_cache.check_for_update()
                for content_access_cert in content_access_certs:
                    self.content_access_cache.update_cert(content_access_cert, update_data)
            if update_data is not None:
                self.ent_dir.refresh()
                self.repo_hook()

        # if we want the full report, we can get it, but
        # this makes CertLib.update() have same sig as reset
        # of *Lib.update
        return self.report

    def install(self, missing_serials):
        """Install any missing entitlement certificates."""

        cert_bundles = self.get_certificates_by_serial_list(missing_serials)

        ent_cert_bundles_installer = EntitlementCertBundlesInstaller(self.report)
        ent_cert_bundles_installer.install(cert_bundles)

    def _find_content_access_certs(self):
        certs = self.ent_dir.list_with_content_access()
        return [cert for cert in certs if cert.entitlement_type == CONTENT_ACCESS_CERT_TYPE]

    def content_access_hook(self):
        if not self.uep.has_capability(CONTENT_ACCESS_CERT_CAPABILITY):
            return  # do nothing if we cannot check for content access cert updates
        content_access_certs = self._find_content_access_certs()
        update_data = None
        if len(content_access_certs) > 0:
            update_data = self.content_access_cache.check_for_update()
        for content_access_cert in content_access_certs:
            self.content_access_cache.update_cert(content_access_cert, update_data)
        if len(content_access_certs) == 0 and self.content_access_cache.exists():
            self.content_access_cache.remove()
        if update_data is not None:
            self.ent_dir.refresh()

    def branding_hook(self):
        """Update branding info based on entitlement cert changes."""

        # RHELBrandsInstaller will use latest ent_dir contents
        brands_installer = rhelentbranding.RHELBrandsInstaller()
        brands_installer.install()

    def repo_hook(self):
        """Update content repos."""
        log.debug("entcerlibaction.repo_hook")
        try:
            # NOTE: this may need a lock
            content_action = content_action_client.ContentActionClient()
            content_action.update()
        except Exception as e:
            log.debug(e)
            log.debug("Failed to update repos")

    def _find_missing_serials(self, local, expected):
        """ Find serials from the server we do not have locally. """
        missing = [sn for sn in expected if sn not in local]
        return missing

    def _find_rogue_serials(self, local, expected):
        """Find serials we have locally but are not on the server."""
        rogue = [local[sn] for sn in local if sn not in expected]
        return rogue

    def syslog_results(self):
        """Write generated EntCertUpdateReport info to syslog."""
        for cert in self.report.added:
            utils.system_log("Added subscription for '%s' contract '%s'" %
                             (cert.order.name, cert.order.contract))
            for product in cert.products:
                utils.system_log("Added subscription for product '%s'" %
                                 (product.name))
        for cert in self.report.rogue:
            utils.system_log("Removed subscription for '%s' contract '%s'" %
                             (cert.order.name, cert.order.contract))
            for product in cert.products:
                utils.system_log("Removed subscription for product '%s'" %
                                 (product.name))

    def _get_local_serials(self):
        local = {}
        # certificates in grace period were being renamed everytime.
        # this makes sure we don't try to re-write certificates in
        # grace period
        # XXX since we don't use grace period, this might not be needed
        self.ent_dir.refresh()
        for valid in self.ent_dir.list():
            sn = valid.serial
            self.report.valid.append(sn)
            local[sn] = valid
        return local

    def get_certificate_serials_list(self):
        """Query RHSM API for list of expected ent cert serial numbers."""
        results = []
        # if there is no UEP object, short circuit
        if self.uep is None:
            return results

        identity = inj.require(inj.IDENTITY)
        if not identity.is_valid():
            # We can get here on unregister, with no id or ent certs or repos,
            # but don't want to raise an exception that would be logged. So
            # empty result set is returned.
            return results

        reply = self.uep.getCertificateSerials(identity.uuid)
        for d in reply:
            sn = d['serial']
            results.append(sn)
        return results

    def get_certificates_by_serial_list(self, sn_list):
        """Fetch a list of entitlement certificates specified by a list of serial numbers."""
        result = []
        if sn_list:
            sn_list = [str(sn) for sn in sn_list]
            # NOTE: use injected IDENTITY, need to validate this
            # handles disconnected errors properly
            reply = self.uep.getCertificates(self.identity.uuid,
                                              serials=sn_list)
            for cert in reply:
                result.append(cert)
        return result

    def _get_expected_serials(self):
        exp = self.get_certificate_serials_list()
        self.report.expected = exp
        return exp

    def delete(self, rogue):
        for cert in rogue:
            try:
                cert.delete()
                self.report.rogue.append(cert)
            except OSError as er:
                log.exception(er)
                log.warn("Failed to delete cert")

        # If we just deleted certs, we need to refresh the now stale
        # entitlement directory before we go to delete expired certs.
        rogue_count = len(self.report.rogue)
        if rogue_count > 0:
            print(ungettext("%s local certificate has been deleted.",
                            "%s local certificates have been deleted.",
                            rogue_count) % rogue_count)
            self.ent_dir.refresh()


class EntitlementCertBundlesInstaller(object):
    """Install a list of entitlement cert bundles.

    pre_install() is triggered before any of the ent cert
    bundles are installed. post_install() is triggered after
    all of the ent cert bundles are installed.
    """

    def __init__(self, report):
        self.exceptions = []
        self.report = report

    def install(self, cert_bundles):
        """Fetch entitliement certs, install them, and update the report."""
        bundle_installer = EntitlementCertBundleInstaller(self.report)
        for cert_bundle in cert_bundles:
            bundle_installer.install(cert_bundle)
        self.exceptions = bundle_installer.exceptions
        self.post_install()

    # TODO: add subman plugin slot,conduit,hooks
    def pre_install(self):
        """Hook called before any ent cert bundles are installed."""
        log.debug("cert bundles pre_install")

    def post_install(self):
        """Hook called after all cert bundles have been installed."""
        for installed in self._get_installed():
            log.debug("cert bundles post_install: %s" % installed)

    def get_installed(self):
        """Return a list of the ent cert bundles that were installed."""
        return self._get_installed()

    def _get_installed(self):
        """Return the bundles installed based on this impl's EntCertUpdateReport."""
        return self.report.added


class EntitlementCertBundleInstaller(object):
    """Install an entitlement cert bundle (cert/key).

    Split a bundle into an certificate.EntitlementCertificate and a
    certificate.Key, and persist them.

    pre_install() is called before the cert bundle is installed.
    post_install() is called after the cert bundle is installed.
    Note that EntitlementCertBundlesInstaller's pre and post install
    hooks are before and after installing the full list of ent cert
    bundles, while this is pre/post each ent cert bundle.
    """

    def __init__(self, report):
        self.exceptions = []
        self.report = report

    def install(self, bundle):
        """Persist an ent cert and it's key after splitting it from the bundle."""
        self.pre_install(bundle)

        cert_bundle_writer = Writer()
        try:
            key, cert = self.build_cert(bundle)
            cert_bundle_writer.write(key, cert)

            self.report.added.append(cert)
        except Exception as e:
            self.install_exception(bundle, e)

        self.post_install(bundle)

    # TODO: add subman plugin, slot, and conduit
    def pre_install(self, bundle):
        """Hook called before an ent cert bundle is installed."""
        log.debug("Ent cert bundle pre_install")

    # should probably be in python-rhsm/certificate
    def build_cert(self, bundle):
        """Split a cert bundle into a EntitlementCertificate and a Key."""
        keypem = bundle['key']
        crtpem = bundle['cert']

        key = Key(keypem)
        cert = create_from_pem(crtpem)

        return (key, cert)

    def install_exception(self, bundle, exception):
        """Log exceptions and add them to the EntCertUpdateReport."""
        log.exception(exception)
        log.error('Bundle not loaded:\n%s\n%s', bundle, exception)

        self.report._exceptions.append(exception)

    def post_install(self, bundle):
        """Hook called after an ent cert bundle is installed."""
        log.debug("ent cert bundle post_install")


class Disconnected(Exception):
    pass


class EntCertUpdateReport(certlib.ActionReport):
    """Report entitlement cert update action changes."""
    name = "Entitlement Cert Updates"

    def __init__(self):
        self.valid = []
        self.expected = []
        self.added = []
        self.rogue = []
        self._exceptions = []

    def updates(self):
        """Total number of ent certs installed and deleted."""
        return (len(self.added) + len(self.rogue))

    # need an ExceptionsReport?
    # FIXME: needs to be properties
    def exceptions(self):
        return self._exceptions

    def write(self, s, title, certificates):
        """Generate a report stanza for a list of certs."""
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
        """__str__ of report. Used in rhsm and rhsmcertd logging."""
        s = []
        s.append(_('Total updates: %d') % self.updates())
        s.append(_('Found (local) serial# %s') % self.valid)
        s.append(_('Expected (UEP) serial# %s') % self.expected)
        self.write(s, _('Added (new)'), self.added)
        self.write(s, _('Deleted (rogue):'), self.rogue)
        return '\n'.join(s)
