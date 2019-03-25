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

log = logging.getLogger(__name__)


class AttachService(object):
    def __init__(self, cp):
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.identity = inj.require(inj.IDENTITY)
        self.cp = cp

    def attach_auto(self, service_level):

        if service_level is not None:
            self.cp.updateConsumer(self.identity.uuid, service_level=service_level)
            log.debug("Service level set to: %s" % service_level)

        self.plugin_manager.run(
            "pre_auto_attach",
            consumer_uuid=self.identity.uuid
        )

        resp = self.cp.bind(self.identity.uuid)

        self.plugin_manager.run(
            "post_auto_attach",
            consumer_uuid=self.identity.uuid,
            entitlement_data=resp
        )

        return resp

    def attach_pool(self, pool, quantity):

        # If quantity is None, server will assume 1. pre_subscribe will
        # report the same.
        self.plugin_manager.run(
            "pre_subscribe",
            consumer_uuid=self.identity.uuid,
            pool_id=pool,
            quantity=quantity
        )

        resp = self.cp.bindByEntitlementPool(self.identity.uuid, pool, quantity)

        self.plugin_manager.run(
            "post_subscribe",
            consumer_uuid=self.identity.uuid,
            entitlement_data=resp
        )

        return resp
