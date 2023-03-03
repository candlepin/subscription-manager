# Copyright (c) 2022 Red Hat, Inc.
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

"""
This module provides service for refreshing entitlement certificates
"""


import logging

from rhsm.connection import UEPConnection

import subscription_manager.injection as inj
from subscription_manager.entcertlib import EntCertActionInvoker

log = logging.getLogger(__name__)


class Refresh:
    """
    Class used for refreshing entitlement certificates
    """

    def __init__(self, cp: UEPConnection = None, ent_cert_lib: EntCertActionInvoker = None) -> None:
        """
        Initialize Refresh object
        """
        if cp is not None:
            self.cp = cp
        else:
            cp_provider = inj.require(inj.CP_PROVIDER)
            self.cp = cp_provider.get_consumer_auth_cp()
        if ent_cert_lib is not None:
            self.ent_cert_lib = ent_cert_lib
        else:
            self.ent_cert_lib = EntCertActionInvoker()

    def refresh(self, force: bool = False) -> None:
        """
        Try to refresh entitlement certificates installed on the system. This method
        can raise some exceptions, when it wasn't possible to refresh entitlement
        certificate(s).
        :param force: Force regeneration of entitlement certificates on the server
        :return: None
        """

        # First remove the content access mode cache to be sure we display
        # SCA or regular mode correctly
        content_access_mode = inj.require(inj.CONTENT_ACCESS_MODE_CACHE)
        if content_access_mode.exists():
            content_access_mode.delete_cache()

        # Remove the release status cache, in case it was changed
        # on the server; it will be fetched when needed again
        inj.require(inj.RELEASE_STATUS_CACHE).delete_cache()

        if force is True:
            # Get current consumer identity
            consumer_identity = inj.require(inj.IDENTITY)
            # Force a regeneration of the entitlement certs for this consumer
            if not self.cp.regenEntitlementCertificates(consumer_identity.uuid, True):
                log.debug("Warning: Unable to refresh entitlement certificates; service likely unavailable")

        self.ent_cert_lib.update()
        log.debug("Refreshed local data")
