from __future__ import print_function, division, absolute_import

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
from subscription_manager import cp_provider

from rhsm import connection

log = logging.getLogger(__name__)


class AttachService(object):
    def __init__(self, connection_info=None):
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.identity = inj.require(inj.IDENTITY)
        self.cp = None

        if isinstance(connection_info, cp_provider.CPProvider):
            self.cp_provider = connection_info
        elif isinstance(connection_info, connection.UEPConnection):
            self.cp = connection_info
        else:
            self.cp_provider = inj.require(inj.CP_PROVIDER)
            if connection_info:
                self.cp_provider.set_connection_info(**connection_info)

    def _connect(self):
        return self.cp or self.cp_provider.get_consumer_auth_cp()

    def attach_auto(self, service_level):
        cp = self._connect()

        if service_level is not None:
            cp.updateConsumer(self.identity.uuid, service_level=service_level)
            log.info("Service level set to: %s" % service_level)

        self.plugin_manager.run("pre_auto_attach", consumer_uuid=self.identity.uuid)
        ents = cp.bind(self.identity.uuid)
        self.plugin_manager.run("post_auto_attach", consumer_uuid=self.identity.uuid, entitlement_data=ents)
        return ents

    def attach_pool(self, pool, quantity):
        cp = self._connect()

        # If quantity is None, server will assume 1. pre_subscribe will
        # report the same.
        self.plugin_manager.run(
            "pre_subscribe",
            consumer_uuid=self.identity.uuid,
            pool_id=pool,
            quantity=quantity
        )

        ents = cp.bindByEntitlementPool(self.identity.uuid, pool, quantity)

        self.plugin_manager.run(
            "post_subscribe",
            consumer_uuid=self.identity.uuid,
            entitlement_data=ents
        )

        return ents
