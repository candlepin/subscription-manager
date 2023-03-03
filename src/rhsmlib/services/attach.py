# Copyright (c) 2017 Red Hat, Inc.
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
import logging

from subscription_manager import injection as inj
from rhsm.connection import UEPConnection

log = logging.getLogger(__name__)


class AttachService:
    """
    Service using for attach pools by ID or auto-attaching
    """

    def __init__(self, cp: UEPConnection) -> None:
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.identity = inj.require(inj.IDENTITY)
        self.cp = cp

    def attach_auto(self, service_level: str = None) -> dict:
        """
        Try to perform auto-attach. Candlepin server tries to attach pool according
        installed product certificates and other attributes (service_level, syspurpose, etc.)
        :param service_level: String with requested service level
        :return: Dictionary with result of REST-API call
        """

        # FIXME: First check if current service_level is the same as provided in
        # argument and if not then try to set something new. Otherwise it is useless
        # and it only cause unnecessary REST API call
        if service_level is not None:
            self.cp.updateConsumer(self.identity.uuid, service_level=service_level)
            log.debug("Service level set to: %s" % service_level)

        self.plugin_manager.run(
            "pre_auto_attach",
            consumer_uuid=self.identity.uuid,
        )

        resp = self.cp.bind(self.identity.uuid)

        self.plugin_manager.run(
            "post_auto_attach",
            consumer_uuid=self.identity.uuid,
            entitlement_data=resp,
        )

        return resp

    def attach_pool(self, pool: str, quantity: int) -> dict:
        """
        Try to attach pool
        :param pool: String with pool ID
        :param quantity: Quantity of subscriptions user wants to consume
        :return: Dictionary with result of REST-API call
        """

        # If quantity is None, server will assume 1. pre_subscribe will
        # report the same.
        self.plugin_manager.run(
            "pre_subscribe", consumer_uuid=self.identity.uuid, pool_id=pool, quantity=quantity
        )

        resp = self.cp.bindByEntitlementPool(self.identity.uuid, pool, quantity)

        self.plugin_manager.run(
            "post_subscribe",
            consumer_uuid=self.identity.uuid,
            entitlement_data=resp,
        )

        return resp
