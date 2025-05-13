# Copyright (c) 2011 Red Hat, Inc.
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
from copy import copy
from datetime import datetime
import logging
from typing import Callable, Dict, List, Optional, Set, TYPE_CHECKING

from rhsm.certificate import GMT
from rhsm.connection import RestlibException
from rhsmlib import file_monitor

import subscription_manager.injection as inj
from subscription_manager.i18n import ugettext as _
from subscription_manager.reasons import Reasons
from subscription_manager import utils

if TYPE_CHECKING:
    from rhsm.certificate2 import EntitlementCertificate
    from subscription_manager.cache import InstalledProductsManager
    from subscription_manager.certdirectory import ProductDirectory, EntitlementDirectory
    from subscription_manager.cp_provider import CPProvider
    from subscription_manager.identity import Identity

log = logging.getLogger(__name__)


# Strings used fot status of system
# Warning: Do not change following strings, because these strings
# are in D-Bus API. The API is used by other applications (Anaconda,
# Cockpit, GNOME, ...)
DISABLED = "disabled"
"""Registered system"""
UNKNOWN = "unknown"
"""Not registered system"""


SOCKET_FACT = "cpu.cpu_socket(s)"
RAM_FACT = "memory.memtotal"

RHSM_VALID = 0
RHSM_EXPIRED = 1
RHSM_WARNING = 2
RHN_CLASSIC = 3
RHSM_PARTIALLY_VALID = 4
RHSM_REGISTRATION_REQUIRED = 5


class ComplianceManager:
    def __init__(self, on_date: Optional[datetime] = None):
        self.cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        self.product_dir: ProductDirectory = inj.require(inj.PROD_DIR)
        self.entitlement_dir: EntitlementDirectory = inj.require(inj.ENT_DIR)
        self.identity: Identity = inj.require(inj.IDENTITY)
        self.on_date: datetime = on_date
        self.installed_products: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.unentitled_products: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.expired_products: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.partially_valid_products: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.valid_products: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.partial_stacks: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.future_products: Optional[Dict[str, List[EntitlementCertificate]]] = None
        self.reasons: Optional[Reasons] = None
        self.supports_reasons: bool = False
        self.system_status: Optional[str] = None
        self.valid_entitlement_certs: Optional[List[EntitlementCertificate]] = None
        self.status: Optional[str] = None
        self.compliant_until: Optional[datetime] = None
        self.load()

    def load(self) -> None:
        # All products installed on this machine, regardless of status. Maps
        # installed product ID to product certificate.
        self.installed_products = self.product_dir.get_installed_products()

        # Installed products which do not have an entitlement that is valid,
        # or expired. They may however have entitlements for the future.
        # Maps installed product ID to the product certificate.
        self.unentitled_products = {}

        # Products which are installed, there are entitlements, but they have
        # expired on the date in question. If another valid or partially valid
        # entitlement provides the installed product, that product should not
        # appear in this dict.
        # Maps product ID to the expired entitlement certificate:
        self.expired_products = {}

        # Products that are only partially entitled (aka, "yellow"). If another
        # non-stacked entitlement is valid and provides the installed product,
        # it will not appear in this dict.
        # Maps installed product ID to the stacked entitlement certificates
        # providing it.
        self.partially_valid_products = {}

        # Products which are installed, and entitled on the given date.
        # Maps product ID to a list of all valid entitlement certificates:
        self.valid_products = {}

        # Maps stack ID to a list of the entitlement certs composing a
        # partially valid stack:
        self.partial_stacks = {}

        # Products which are installed and entitled sometime in the future.
        # Maps product ID to future entitlements.
        self.future_products = {}

        # Reasons that products aren't fully compliant
        self.reasons = Reasons([], self)
        self.supports_reasons = False
        self.system_status = UNKNOWN
        self.valid_entitlement_certs = []
        self.compliant_until = None

        if self.is_registered():
            self._scan_entitlement_certs()
            self.log_products()
            self.system_status = DISABLED

    def log_products(self) -> None:
        fj: Callable = utils.friendly_join

        log.debug(
            "Product status: valid_products=%s partial_products=%s expired_products=%s"
            " unentitled_producs=%s future_products=%s valid_until=%s",
            fj(list(self.valid_products.keys())),
            fj(list(self.partially_valid_products.keys())),
            fj(list(self.expired_products.keys())),
            fj(list(self.unentitled_products.keys())),
            fj(list(self.future_products.keys())),
            self.compliant_until,
        )

        log.debug("partial stacks: %s" % list(self.partial_stacks.keys()))

    def _scan_entitlement_certs(self) -> None:
        """
        Scan entitlement certs looking for unentitled products which may
        have expired, or be entitled in future.

        Also builds up a list of valid certs today. (used when determining
        if anything is in it's warning period)
        """
        # Subtract out the valid and partially valid items from the
        # list of installed products
        unknown_products = dict(
            (k, v)
            for (k, v) in list(self.installed_products.items())
            if k not in list(self.valid_products.keys())
            and k not in list(self.partially_valid_products.keys())
        )
        ent_certs: List[EntitlementCertificate] = self.entitlement_dir.list()

        on_date: datetime = datetime.now(GMT())
        ent_cert: EntitlementCertificate
        for ent_cert in ent_certs:
            # Builds the list of valid entitlement certs today:
            if ent_cert.is_valid():
                self.valid_entitlement_certs.append(ent_cert)

            for product in ent_cert.products:
                if product.id in list(unknown_products.keys()):
                    # If the entitlement starts after the date we're checking, we
                    # consider this a future entitlement. Technically it could be
                    # partially stacked on that date, but we cannot determine that
                    # without recursively cert sorting again on that date.
                    if ent_cert.valid_range.begin() > on_date:
                        product_dict = self.future_products
                    # Check if entitlement has already expired:
                    elif ent_cert.valid_range.end() < on_date:
                        product_dict = self.expired_products
                    else:
                        continue

                    product_dict.setdefault(product.id, []).append(ent_cert)

    def get_system_status_id(self) -> Optional[str]:
        return self.system_status

    @staticmethod
    def get_status_map() -> Dict[str, str]:
        """
        Get status map
        :return: status map
        """
        # Status map has to be here, because we have to translate strings
        # when function is called (not during start of application) due to
        # rhsm.service which can run for very long time
        status_map = {
            DISABLED: _("Disabled"),
            UNKNOWN: _("Unknown"),
        }
        return status_map

    def get_system_status(self) -> str:
        status_map: Dict[str, str] = self.get_status_map()
        return status_map.get(self.system_status, status_map[UNKNOWN])

    def are_reasons_supported(self) -> bool:
        # Check if the candlepin in use supports status
        # detail messages. Older versions don't.
        return self.supports_reasons

    def is_valid(self) -> bool:
        """
        Return true if the results of this cert sort indicate our
        entitlements are completely valid.
        """
        return self.system_status == DISABLED

    def is_registered(self) -> bool:
        return inj.require(inj.IDENTITY).is_valid()

    def get_status(self, product_id: str) -> str:
        """Return the status of a given product"""
        if not self.is_registered():
            return UNKNOWN
        return DISABLED

    def in_warning_period(self) -> bool:
        for entitlement in self.valid_entitlement_certs:
            if entitlement.is_expiring():
                return True
        return False

    # Assumes classic and identity validity have been tested
    def get_status_for_icon(self) -> int:
        if self.system_status == "invalid":
            return RHSM_EXPIRED
        if self.system_status == "partial":
            return RHSM_PARTIALLY_VALID
        if self.in_warning_period():
            return RHSM_WARNING
        return RHSM_VALID  # Correct when unknown


class CertSorter(ComplianceManager):
    """
    Queries the server for compliance information and breaks out the response
    for use in the client code.

    Originally this class actually sorted certificates and calculated status,
    but this is handled by the server today.

    If unregistered we report status as unknown.

    On every successful server fetch (for *right now*), we cache the results.
    In the event we are unable to reach the server periodically, we will
    re-use this cached data for a period of time, before falling back to
    reporting unknown.
    """

    def __init__(self, on_date: datetime = None):
        # Sync installed product info with server.
        # This will be done on register if we aren't registered.
        # ComplianceManager.__init__ needs the installed product info
        # in sync before it will be accurate, so update it, then
        # super().__init__. See rhbz #1004893
        self.installed_mgr: InstalledProductsManager = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)
        self.update_product_manager()

        super(CertSorter, self).__init__(on_date)
        self.callbacks: Set[Callable] = set()

        cert_dir_monitors: Dict[str, file_monitor.DirectoryWatch] = {
            file_monitor.PRODUCT_WATCHER: file_monitor.DirectoryWatch(
                inj.require(inj.PROD_DIR).path, [self.on_prod_dir_changed, self.load]
            ),
            file_monitor.ENTITLEMENT_WATCHER: file_monitor.DirectoryWatch(
                inj.require(inj.ENT_DIR).path, [self.on_ent_dir_changed, self.load]
            ),
            file_monitor.CONSUMER_WATCHER: file_monitor.DirectoryWatch(
                inj.require(inj.IDENTITY).cert_dir_path, [self.on_identity_changed, self.load]
            ),
        }

        # Note: no timer is setup to poll file_monitor by cert_sorter itself,
        # the gui can add one.
        self.cert_monitor = file_monitor.FilesystemWatcher(cert_dir_monitors)

    def update_product_manager(self) -> None:
        if self.is_registered():
            cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
            consumer_identity: Identity = inj.require(inj.IDENTITY)
            try:
                self.installed_mgr.update_check(cp_provider.get_consumer_auth_cp(), consumer_identity.uuid)
            except RestlibException:
                # Invalid consumer certificate
                pass

    def force_cert_check(self) -> None:
        updated: Set[file_monitor.DirectoryWatch] = self.cert_monitor.update()
        if updated:
            self.notify()

    def notify(self) -> None:
        callback: Callable
        for callback in copy(self.callbacks):
            callback()

    def add_callback(self, cb: Callable) -> None:
        self.callbacks.add(cb)

    def remove_callback(self, cb: Callable) -> bool:
        try:
            self.callbacks.remove(cb)
            return True
        except KeyError:
            return False

    def on_change(self) -> None:
        self.load()
        self.notify()

    def on_certs_changed(self) -> None:
        # Now that local data has been refreshed, updated compliance
        self.on_change()

    def on_prod_dir_changed(self) -> None:
        """
        Callback method, when content of directory with product certificates has been changed
        """
        self.product_dir.refresh()
        self.update_product_manager()

    def on_ent_dir_changed(self) -> None:
        """
        Callback method, when content of directory with entitlement certificates has been changed
        """
        self.entitlement_dir.refresh()

    def on_identity_changed(self) -> None:
        """
        Callback method, when content of directory with consumer certificate has been changed
        """
        self.identity.reload()
        self.cp_provider.clean()

    # check to see if there are certs in the directory
    def has_entitlements(self) -> bool:
        return len(self.entitlement_dir.list()) > 0


class StackingGroupSorter:
    def __init__(self, entitlements: List["EntitlementCertificate"]):
        self.groups: List[EntitlementGroup] = []
        stacking_groups: Dict[str, EntitlementGroup] = {}

        for entitlement in entitlements:
            stacking_id: Optional[str] = self._get_stacking_id(entitlement)
            if stacking_id:
                group: EntitlementGroup
                if stacking_id not in stacking_groups:
                    group = EntitlementGroup(entitlement, self._get_identity_name(entitlement))
                    self.groups.append(group)
                    stacking_groups[stacking_id] = group
                else:
                    group = stacking_groups[stacking_id]
                    group.add_entitlement_cert(entitlement)
            else:
                self.groups.append(EntitlementGroup(entitlement))

    def _get_stacking_id(self, entitlement: "EntitlementCertificate"):
        raise NotImplementedError("Subclasses must implement: _get_stacking_id")

    def _get_identity_name(self, entitlement: "EntitlementCertificate"):
        raise NotImplementedError("Subclasses must implement: _get_identity_name")


class EntitlementGroup:
    def __init__(self, entitlement: "EntitlementCertificate", name: str = ""):
        self.name = name
        self.entitlements: List[EntitlementCertificate] = []
        self.add_entitlement_cert(entitlement)

    def add_entitlement_cert(self, entitlement: "EntitlementCertificate") -> None:
        self.entitlements.append(entitlement)


class EntitlementCertStackingGroupSorter(StackingGroupSorter):
    def __init__(self, certs: List["EntitlementCertificate"]):
        StackingGroupSorter.__init__(self, certs)

    def _get_stacking_id(self, cert: "EntitlementCertificate") -> Optional[str]:
        if cert.order:
            return cert.order.stacking_id
        else:
            return None

    def _get_identity_name(self, cert: "EntitlementCertificate") -> Optional[str]:
        if cert.order:
            return cert.order.name
        else:
            return None
