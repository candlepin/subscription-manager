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

import logging

from subscription_manager import base_action_client
from subscription_manager import certlib
from subscription_manager import repolib
from subscription_manager.model.ent_cert import EntitlementDirEntitlementSource

import subscription_manager.injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class ContentPluginActionReport(certlib.ActionReport):
    """Aggragate the info reported by each content plugin.

    Just a set of reports that include info about the content
    plugin that created it.
    """
    name = "Content Plugin Reports"

    def __init__(self):
        super(ContentPluginActionReport, self).__init__()
        self.reports = set()

    def add(self, report):
        # report should include info about what plugin generated it
        self.reports.add(report)


class ContentPluginActionCommand(object):
    """An ActionCommand used to wrap 'content_update' plugin invocations.

    args:
        content_plugin_runner: a PluginHookRunner created with
              PluginManager.runiter('content_update').runiter()

    perform() runs the PluginHookRunner and returns the ContentActionReport
      that PluginHookRunner.run() adds to the content plugin conduit.
    """
    def __init__(self, content_plugin_runner):
        self.runner = content_plugin_runner

    def perform(self):
        self.runner.run()
        # Actually a set of reports...
        return self.runner.conduit.reports


class ContentPluginActionInvoker(certlib.BaseActionInvoker):
    """ActionInvoker for ContentPluginActionCommands."""
    def __init__(self, content_plugin_runner):
        """Create a ContentPluginActionInvoker to wrap content plugin PluginHookRunner.

        Pass a PluginHookRunner to ContentPluginActionCommand. Do the
        normal ActionInvoker tasks and collect ActionReports.

        args:
            content_plugin_runner: a PluginHookRunner created with
              PluginManager.runiter('content_update').runiter()
        """
        super(ContentPluginActionInvoker, self).__init__()
        self.runner = content_plugin_runner

    def _do_update(self):
        action = ContentPluginActionCommand(self.runner)
        return action.perform()


class ContentActionClient(base_action_client.BaseActionClient):

    def _get_libset(self):
        """Return a generator that creates a ContentPluginAction* for each update_content plugin.

        The iterable return includes the yum repo action invoker, and a ContentPluginActionInvoker
        for each plugin hook mapped to the 'update_content_hook' slot.
        """

        yield repolib.RepoActionInvoker()

        plugin_manager = inj.require(inj.PLUGIN_MANAGER)

        content_plugins_reports = ContentPluginActionReport()

        # Ent dir is our only source of entitlement/content info atm
        # NOTE: this is created and populated with the content of
        # the ent dir before the plugins are run and it doesn't
        # update.
        ent_dir_ent_source = EntitlementDirEntitlementSource()

        for runner in plugin_manager.runiter('update_content',
                                             reports=content_plugins_reports,
                                             ent_source=ent_dir_ent_source):
            invoker = ContentPluginActionInvoker(runner)
            yield invoker
