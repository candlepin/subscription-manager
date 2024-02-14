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
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

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

from subscription_manager import repolib
from subscription_manager.i18n import ungettext, ugettext as _

if TYPE_CHECKING:
    from rhsm.connection import UEPConnection
    from rhsm.certificate2 import Product

    from subscription_manager.cache import ContentAccessCache
    from subscription_manager.cp_provider import CPProvider
    from subscription_manager.identity import Identity
    from subscription_manager.certdirectory import EntitlementCertificate, EntitlementDirectory


log = logging.getLogger(__name__)

CONTENT_ACCESS_CERT_CAPABILITY = "org_level_content_access"


class EntCertActionInvoker(certlib.BaseActionInvoker):
    """Invoker for entitlement certificate updating actions."""

    def _do_update(self) -> "EntCertUpdateReport":
        action = EntCertUpdateAction()
        return action.perform()


class EntCertUpdateAction:
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
        self.cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        self.uep: UEPConnection = self.cp_provider.get_consumer_auth_cp()
        self.ent_dir: EntitlementDirectory = inj.require(inj.ENT_DIR)
        self.identity: Identity = require(IDENTITY)
        self.report = EntCertUpdateReport()
        self.content_access_cache: ContentAccessCache = inj.require(inj.CONTENT_ACCESS_CACHE)

    # NOTE: this is slightly at odds with the manual cert import
    #       path, manual import certs won't get a 'report', etc
    def perform(self) -> "EntCertUpdateReport":
        local: Dict[int, EntitlementCertificate] = self._get_local_serials()
        try:
            expected: List[int] = self._get_expected_serials()
        except socket.error as ex:
            log.exception(ex)
            log.error("Cannot modify subscriptions while disconnected")
            raise Disconnected()

        cert_changed: bool = False
        missing_serials: List[int] = self._find_missing_serials(local, expected)
        rogue_serials: List[EntitlementCertificate] = self._find_rogue_serials(local, expected)

        self.delete(rogue_serials)
        installed_serials: List[int] = self.install(missing_serials)

        log.info("certs updated:\n%s", self.report)
        self.syslog_results()

        # We call EntCertlibActionInvoker.update() solo from
        # the 'attach' cli instead of an ActionClient. So
        # we need to refresh the ent_dir object before calling
        # content updating actions.
        self.ent_dir.refresh()

        if missing_serials or rogue_serials:
            cert_changed = True

        if self.uep.has_capability(CONTENT_ACCESS_CERT_CAPABILITY):
            content_access_certs: List[EntitlementCertificate] = self._find_content_access_certs()
            if len(content_access_certs) > 0:
                # This addresses BZs: 1448855, 1450862
                obsolete_certs: List[EntitlementCertificate] = []
                for cont_access_cert in content_access_certs:
                    if cont_access_cert.serial in installed_serials:
                        continue
                    if cont_access_cert.serial not in expected:
                        obsolete_certs.append(cont_access_cert)
                if len(obsolete_certs) > 0:
                    log.info("Deleting obsolete content access certificate")
                    self.delete(obsolete_certs)
            update_data: Optional[Dict] = self.content_access_hook()
            if update_data is not None:
                cert_changed = True

        if cert_changed:
            self.repo_hook()

            # NOTE: Since we have the yum repos defined here now
            #       we could update product id certs here, or install
            #       them if they are needed, but missing. That way the
            #       branding installs could be more accurate.

            # reload certs and update branding
            self.branding_hook()

        # if we want the full report, we can get it, but
        # this makes CertLib.update() have same sig as reset
        # of *Lib.update
        return self.report

    def install(self, missing_serials) -> List[int]:
        """Install any missing entitlement certificates."""

        cert_bundles = self.get_certificates_by_serial_list(missing_serials)

        ent_cert_bundles_installer = EntitlementCertBundlesInstaller(self.report)
        return ent_cert_bundles_installer.install(cert_bundles)

    def _find_content_access_certs(self) -> List["EntitlementCertificate"]:
        certs: List[EntitlementCertificate] = self.ent_dir.list_with_content_access()
        return [cert for cert in certs if cert.entitlement_type == CONTENT_ACCESS_CERT_TYPE]

    def content_access_hook(self) -> Optional[Dict]:
        if not self.uep.has_capability(CONTENT_ACCESS_CERT_CAPABILITY):
            return  # do nothing if we cannot check for content access cert updates
        content_access_certs: List[EntitlementCertificate] = self._find_content_access_certs()
        update_data: Optional[Dict] = None
        if len(content_access_certs) > 0:
            update_data = self.content_access_cache.check_for_update()
        for content_access_cert in content_access_certs:
            self.content_access_cache.update_cert(content_access_cert, update_data)
        if len(content_access_certs) == 0 and self.content_access_cache.exists():
            self.content_access_cache.remove()
        if update_data is not None:
            self.ent_dir.refresh()
        return update_data

    def branding_hook(self) -> None:
        """Update branding info based on entitlement cert changes."""

        # RHELBrandsInstaller will use latest ent_dir contents
        brands_installer = rhelentbranding.RHELBrandsInstaller()
        brands_installer.install()

    def repo_hook(self) -> None:
        """Update content repos."""
        log.debug("entcerlibaction.repo_hook")
        try:
            # NOTE: this may need a lock
            content_action = content_action_client.ContentActionClient()
            content_action.update()
        except Exception as e:
            log.debug(e)
            log.debug("Failed to update repos")

    def _find_missing_serials(
        self, local: Dict[int, "EntitlementCertificate"], expected: List[int]
    ) -> List[int]:
        """Find serials from the server we do not have locally."""
        missing = [sn for sn in expected if sn not in local]
        return missing

    def _find_rogue_serials(
        self, local: Dict[int, "EntitlementCertificate"], expected: List[int]
    ) -> List["EntitlementCertificate"]:
        """Find serials we have locally but are not on the server."""
        rogue = [local[sn] for sn in local if sn not in expected]
        return rogue

    def syslog_results(self) -> None:
        """Write generated EntCertUpdateReport info to syslog."""
        for cert in self.report.added:
            utils.system_log(
                "Added subscription for '%s' contract '%s'" % (cert.order.name, cert.order.contract)
            )
            for product in cert.products:
                utils.system_log("Added subscription for product '%s'" % (product.name))
        for cert in self.report.rogue:
            utils.system_log(
                "Removed subscription for '%s' contract '%s'" % (cert.order.name, cert.order.contract)
            )
            for product in cert.products:
                utils.system_log("Removed subscription for product '%s'" % (product.name))

    def _get_local_serials(self) -> Dict[int, "EntitlementCertificate"]:
        local: Dict[int, EntitlementCertificate] = {}
        # certificates in grace period were being renamed everytime.
        # this makes sure we don't try to re-write certificates in
        # grace period
        # XXX since we don't use grace period, this might not be needed
        self.ent_dir.refresh()
        ent_certs: List[EntitlementCertificate] = (
            self.ent_dir.list() + self.ent_dir.list_with_content_access()
        )
        ent_certs = list(set(ent_certs))
        for valid in ent_certs:
            sn: int = valid.serial
            self.report.valid.append(sn)
            local[sn] = valid
        return local

    def get_certificate_serials_list(self) -> List[int]:
        """Query RHSM API for list of expected ent cert serial numbers."""
        results: List[int] = []
        # if there is no UEP object, short circuit
        if self.uep is None:
            return results

        identity: Identity = inj.require(inj.IDENTITY)
        if not identity.is_valid():
            # We can get here on unregister, with no id or ent certs or repos,
            # but don't want to raise an exception that would be logged. So
            # empty result set is returned.
            return results

        reply: List[Dict] = self.uep.getCertificateSerials(identity.uuid)
        for d in reply:
            sn: int = d["serial"]
            results.append(sn)
        return results

    def get_certificates_by_serial_list(self, sn_list: List[int]) -> List[Dict]:
        """Fetch a list of entitlement certificates specified by a list of serial numbers."""
        result: List[Dict] = []
        if sn_list:
            sn_list = [str(sn) for sn in sn_list]
            # NOTE: use injected IDENTITY, need to validate this
            # handles disconnected errors properly
            reply: List[Dict] = self.uep.getCertificates(self.identity.uuid, serials=sn_list)
            for cert in reply:
                result.append(cert)
        return result

    def _get_expected_serials(self) -> List[int]:
        exp: List[int] = self.get_certificate_serials_list()
        self.report.expected = exp
        return exp

    def delete(self, rogue: List["EntitlementCertificate"]):
        for cert in rogue:
            try:
                cert.delete()
                self.report.rogue.append(cert)
            except OSError as er:
                log.exception(er)
                log.warning("Failed to delete cert")

        # If we just deleted certs, we need to refresh the now stale
        # entitlement directory before we go to delete expired certs.
        rogue_count: int = len(self.report.rogue)
        if rogue_count > 0:
            print(
                ungettext(
                    "%s local certificate has been deleted.",
                    "%s local certificates have been deleted.",
                    rogue_count,
                )
                % rogue_count
            )
            self.ent_dir.refresh()


class EntitlementCertBundlesInstaller:
    """Install a list of entitlement cert bundles.

    pre_install() is triggered before any of the ent cert
    bundles are installed. post_install() is triggered after
    all of the ent cert bundles are installed.
    """

    def __init__(self, report: "EntCertUpdateReport"):
        self.exceptions: List[Exception] = []
        self.report: EntCertUpdateReport = report

    def install(self, cert_bundles):
        """Fetch entitliement certs, install them, and update the report."""
        bundle_installer = EntitlementCertBundleInstaller(self.report)
        installed_serials: List[int] = []
        for cert_bundle in cert_bundles:
            cert_serial: Optional[int] = bundle_installer.install(cert_bundle)
            if cert_serial is not None:
                installed_serials.append(cert_serial)
        self.exceptions = bundle_installer.exceptions
        self.post_install()
        return installed_serials

    # TODO: add subman plugin slot, conduit, hooks
    def pre_install(self) -> None:
        """Hook called before any ent cert bundles are installed."""
        log.debug("cert bundles pre_install")

    def post_install(self) -> None:
        """Hook called after all cert bundles have been installed."""
        for installed in self._get_installed():
            log.debug("cert bundles post_install: %s" % installed)

    def get_installed(self) -> List["EntitlementCertificate"]:
        """Return a list of the ent cert bundles that were installed."""
        return self._get_installed()

    def _get_installed(self) -> List["EntitlementCertificate"]:
        """Return the bundles installed based on this impl's EntCertUpdateReport."""
        return self.report.added


class EntitlementCertBundleInstaller:
    """Install an entitlement cert bundle (cert/key).

    Split a bundle into an certificate.EntitlementCertificate and a
    certificate.Key, and persist them.

    pre_install() is called before the cert bundle is installed.
    post_install() is called after the cert bundle is installed.
    Note that EntitlementCertBundlesInstaller's pre and post install
    hooks are before and after installing the full list of ent cert
    bundles, while this is pre/post each ent cert bundle.
    """

    def __init__(self, report: "EntCertUpdateReport"):
        self.exceptions: List[EntitlementCertificate] = []
        self.report: EntCertUpdateReport = report

    def install(self, bundle: Dict):
        """Persist an ent cert and it's key after splitting it from the bundle."""
        self.pre_install(bundle)

        cert_bundle_writer = Writer()
        cert_serial: int = None
        try:
            key, cert = self.build_cert(bundle)
            cert_bundle_writer.write(key, cert)
            self.report.added.append(cert)
            cert_serial = cert.serial
        except Exception as e:
            self.install_exception(bundle, e)

        self.post_install(bundle)

        return cert_serial

    # TODO: add subman plugin, slot, and conduit
    def pre_install(self, bundle: Dict):
        """Hook called before an ent cert bundle is installed."""
        log.debug("Ent cert bundle pre_install")

    # should probably be in python-rhsm/certificate
    def build_cert(self, bundle: Dict) -> Tuple[Key, "EntitlementCertificate"]:
        """Split a cert bundle into a EntitlementCertificate and a Key."""
        keypem: str = bundle["key"]
        crtpem: str = bundle["cert"]

        key = Key(keypem)
        cert: EntitlementCertificate = create_from_pem(crtpem)

        return (key, cert)

    def install_exception(self, bundle: Dict, exception: Exception) -> None:
        """Log exceptions and add them to the EntCertUpdateReport."""
        log.exception(exception)
        log.error("Bundle not loaded:\n%s\n%s", bundle, exception)

        self.report._exceptions.append(exception)

    def post_install(self, bundle: Dict) -> None:
        """Hook called after an ent cert bundle is installed."""
        log.debug("ent cert bundle post_install")


class Disconnected(Exception):
    pass


class EntCertUpdateReport(certlib.ActionReport):
    """Report entitlement cert update action changes."""

    name = "Entitlement Cert Updates"

    def __init__(self):
        self.valid: List[EntitlementCertificate] = []
        self.expected: List[EntitlementCertificate] = []
        self.added: List[EntitlementCertificate] = []
        self.rogue: List[EntitlementCertificate] = []
        self._exceptions: List[Exception] = []

    def updates(self) -> int:
        """Total number of ent certs installed and deleted."""
        return len(self.added) + len(self.rogue)

    # need an ExceptionsReport?
    # FIXME: needs to be properties
    def exceptions(self) -> List[Exception]:
        return self._exceptions

    def write(self, s: List[str], title: str, certificates: List["EntitlementCertificate"]) -> None:
        """Generate a report stanza for a list of certs."""
        indent: str = "  "
        s.append(title)
        if certificates:
            for c in certificates:
                products: List[Product] = c.products
                if not products:
                    s.append("%s[sn:%d (%s) @ %s]" % (indent, c.serial, c.order.name, c.path))
                for product in products:
                    s.append("%s[sn:%d (%s,) @ %s]" % (indent, c.serial, product.name, c.path))
        else:
            s.append("%s<NONE>" % indent)

    def __str__(self) -> str:
        """__str__ of report. Used in rhsm and rhsmcertd logging."""
        s = []
        s.append(_("Total updates: %d") % self.updates())
        s.append(_("Found (local) serial# %s") % self.valid)
        s.append(_("Expected (UEP) serial# %s") % self.expected)
        self.write(s, _("Added (new)"), self.added)
        self.write(s, _("Deleted (rogue):"), self.rogue)
        return "\n".join(s)


class AnonymousCertificateManager:
    """Manage anonymous entitlement certificates.

    Anonymous certificate can be obtained from Candlepin via JWT/bearer token
    when the system is deployed as a cloud VM.

    These certificates are short-lived and are meant to be replaced by a proper
    certificate in a short time.
    """

    def __init__(self, uep: "UEPConnection"):
        self.uep = uep

    def install_temporary_certificates(self, uuid: str, jwt: str) -> None:
        """Obtain temporary entitlement certificates.

        - Download and install temporary entitlement certificates and keys
          without obtaining an identity certificate.
        - Generate 'redhat.repo' file out of them.

        :param uuid: The anonymous UUID assigned by Candlepin.
        :param jwt: The Bearer token sent by Candlepin.
        """
        log.debug("Obtaining anonymous entitlement certificates and keys.")
        certificates: List[Dict] = self.uep.getCertificates(consumer_uuid=uuid, jwt=jwt)
        if not len(certificates):
            log.debug("No anonymous entitlement certificates were received.")
            return

        log.debug("Installing anonymous entitlement certificates and keys.")
        report = EntCertUpdateReport()
        installer = EntitlementCertBundlesInstaller(report=report)
        entitlement_ids: List[int] = installer.install(cert_bundles=certificates)

        log.debug(
            "The following anonymous entitlement certificates and keys were installed: "
            + ", ".join(str(c) for c in entitlement_ids)
        )

        update_repo = repolib.RepoUpdateActionCommand()
        update_repo_report: Optional[repolib.RepoActionReport] = update_repo.perform()

        if update_repo_report is None:
            log.debug("Anonymous entitlement certificate did not cause repository updates.")
        else:
            log.debug(
                "Anonymous entitlement certificate caused "
                f"{update_repo_report.updates()} repositories to be updated."
            )
