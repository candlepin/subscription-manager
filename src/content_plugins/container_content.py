from __future__ import print_function, division, absolute_import

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
entitlement certificates, and correctly configure to use them.
"""
from subscription_manager import base_plugin
requires_api_version = "1.1"

from subscription_manager.plugin.container import \
    ContainerContentUpdateActionCommand


class ContainerContentPlugin(base_plugin.SubManPlugin):
    """Plugin for adding docker content action to subscription-manager"""
    name = "container_content"

    # Default location where we'll manage hostname specific directories of
    # certificates.
    HOSTNAME_CERT_DIR = "/etc/docker/certs.d/"

    def update_content_hook(self, conduit):
        """
        Hook to update for any Docker content we have.

        Args:
            conduit: An UpdateContentConduit
        """
        conduit.log.debug("Updating container content.")
        registry_hostnames = conduit.conf_string('main', 'registry_hostnames')
        conduit.log.debug("registry hostnames = %s" % registry_hostnames)
        cmd = ContainerContentUpdateActionCommand(
            ent_source=conduit.ent_source,
            registry_hostnames=registry_hostnames.split(','),
            host_cert_dir=self.HOSTNAME_CERT_DIR)
        report = cmd.perform()
        conduit.reports.add(report)


def main():
    from subscription_manager.plugins import PluginManager
    from subscription_manager import injectioninit
    from subscription_manager.plugins import UpdateContentConduit
    from subscription_manager.model.ent_cert import EntitlementDirEntitlementSource
    from subscription_manager.content_action_client import ContentPluginActionReport

    plugin_manager = PluginManager()
    plugin_class = plugin_manager.get_plugins()['container_content.ContainerContentPlugin']
    plugin = plugin_class()
    injectioninit.init_dep_injection()
    ent_source = EntitlementDirEntitlementSource()
    reports = ContentPluginActionReport()
    conduit = UpdateContentConduit(plugin_class, reports=reports, ent_source=ent_source)
    plugin.update_content_hook(conduit)


if __name__ == "__main__":
    main()
