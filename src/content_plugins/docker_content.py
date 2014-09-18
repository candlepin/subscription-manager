#
# Copyright (c) 2014 Red Hat, Inc.
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
entitlement certificates, and correctly configure docker to use them.
"""

from subscription_manager import base_plugin
requires_api_version = "1.1"

from subscription_manager.plugin.docker import action_invoker


class DockerContentPlugin(base_plugin.SubManPlugin):
    """Plugin for adding docker content action to subscription-manager"""
    name = "docker_content"

    def update_content_hook(self, conduit):
        """
        Hook to update for any docker content we have.

        Args:
            conduit: A UpdateContentConduit
        """
        conduit.log.info("Updating Docker content.")
        for ent in conduit.ent_source:
            conduit.log.debug("ent_source ent: %s" % ent)

        report = action_invoker.DockerContentUpdateActionCommand(ent_source=conduit.ent_source).perform()
        conduit.reports.add(report)
