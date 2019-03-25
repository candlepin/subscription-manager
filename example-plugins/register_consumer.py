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


class RegisterConsumerPlugin(SubManPlugin):
    """Plugin triggered when a consumer registers"""
    name = "register_consumer"

    def post_register_consumer_hook(self, conduit):
        """`post_register_consumer` hook

        Args:
            conduit: A RegistrationConduit()
        """
        conduit.log.debug("post consumer register called")
        conduit.log.debug("consumer uuid: %s" % conduit.consumer['uuid'])

    def pre_register_consumer_hook(self, conduit):
        """`pre_register_consumer` hook

        Args:
            conduit: A RegistrationConduit()
        """
        conduit.log.debug("pre  consumer register called")
        conduit.log.debug("Consumer name: %s" % conduit.name)
        conduit.log.debug("Consumer facts count: %s" % len(conduit.facts))
