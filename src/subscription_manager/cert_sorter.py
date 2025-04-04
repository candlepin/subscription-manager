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
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rhsm.certificate2 import EntitlementCertificate

log = logging.getLogger(__name__)

# Strings used for status of products
FUTURE_SUBSCRIBED = "future_subscribed"
SUBSCRIBED = "subscribed"
NOT_SUBSCRIBED = "not_subscribed"
EXPIRED = "expired"
PARTIALLY_SUBSCRIBED = "partially_subscribed"

# Strings used fot status of system
# Warning: Do not change following strings, because these strings
# are in D-Bus API. The API is used by other applications (Anaconda,
# Cockpit, GNOME, ...)
VALID = "valid"
INVALID = "invalid"
PARTIAL = "partial"
DISABLED = "disabled"
UNKNOWN = "unknown"


SOCKET_FACT = "cpu.cpu_socket(s)"
RAM_FACT = "memory.memtotal"

RHSM_VALID = 0
RHSM_EXPIRED = 1
RHSM_WARNING = 2
RHN_CLASSIC = 3
RHSM_PARTIALLY_VALID = 4
RHSM_REGISTRATION_REQUIRED = 5


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
