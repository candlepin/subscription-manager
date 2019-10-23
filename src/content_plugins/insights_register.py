from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2019 Red Hat, Inc.
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

"""
A subscription-manager plugin to watch for docker content in
entitlement certificates, and correctly configure to use them.
"""
import os
from subscription_manager import base_plugin
from subscription_manager.plugins import API_VERSION
requires_api_version = "1.1"


class InsightsRegisterPlugin(base_plugin.SubManPlugin):
    """Plugin for registering to insights during subscription-manager register"""
    name = "insights_register"

    def post_register_consumer_hook(self, conduit):
        """
        Hook to update for any Docker content we have.

        Args:
            conduit: An UpdateContentConduit
        """
        self._run_insights_client(conduit, 'register')

    if API_VERSION > '1.1':
        def post_unregister_consumer_hook(self, conduit):
            """
            Hook to update for any Docker content we have.

            Args:
                conduit: An UpdateContentConduit
            """
            self._run_insights_client(conduit, 'unregister')

    @staticmethod
    def _run_insights_client(conduit, action):
        cmd = "insights-client --{}".format(action)

        conduit.log.info("Trying to run insights-client to {}".format(action))
        try:
            os.system(cmd)
        except Exception:
            conduit.log.warn(
                'Unable to {} using insights-client, do you have "insights-client" installed?')
