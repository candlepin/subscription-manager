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

from subscription_manager import base_plugin
requires_api_version = "1.1"

# install our helper modules here
from subscription_manager.plugin.ostree import action_invoker


class OstreeContentPlugin(base_plugin.SubManPlugin):
    """Plugin for adding ostree content action to subscription-manager"""
    name = "ostree_content"

    def update_content_hook(self, conduit):
        """
        Hook to update for any OSTree content we have.

        Args:
            conduit: A UpdateContentConduit
        """
        conduit.log.debug("ostree update_content_hook plugin.")

        report = action_invoker.OstreeContentUpdateActionCommand(ent_source=conduit.ent_source).perform()
        conduit.reports.add(report)
