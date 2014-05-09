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
    def perform(self):
        plugin_manager = inj.require(inj.PLUGIN_MANAGER)

        content_plugins_reports = ContentPluginActionReport()
        plugin_manager.run('update_content', reports=content_plugins_reports)

        # Actually a set of reports...
        return content_plugins_reports


class ContentPluginActionInvoker(certlib.BaseActionInvoker):
    def _do_update(self):
        action = ContentPluginActionCommand()
        return action.perform()


class ContentActionClient(base_action_client.BaseActionClient):

    def _get_libset(self):
        self.yum_repo_action_invoker = repolib.RepoActionInvoker()
        self.content_plugin_action_invoker = ContentPluginActionInvoker()

        # TODO: replace libset/_get_libset with a ActionInvokerProvider
        lib_set = [self.yum_repo_action_invoker,
                   self.content_plugin_action_invoker]

        return lib_set
