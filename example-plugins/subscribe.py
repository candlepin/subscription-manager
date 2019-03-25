from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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

from subscription_manager.base_plugin import SubManPlugin
requires_api_version = "1.0"


class SubscribePlugin(SubManPlugin):
    """Plugin triggered when a consumer subscribes to an entitlement"""
    name = "subscribe"

    def pre_subscribe_hook(self, conduit):
        """`pre_subscribe` hook

        Args:
            conduit: A SubscriptionConduit()
        """
        conduit.log.debug("pre subscribe called")

    def post_subscribe_hook(self, conduit):
        """`post_subscribe` hook

        Args:
            conduit: A PostSubscriptionConduit()
        """
        conduit.log.debug("post subscribe called")

    def pre_auto_attach_hook(self, conduit):
        conduit.log.debug("pre auto attach called")

    def post_auto_attach_hook(self, conduit):
        conduit.log.debug("post auto attach called")
