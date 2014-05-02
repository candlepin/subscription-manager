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
from subscription_manager import repolib
from subscription_manager import ostree_action_invoker
import subscription_manager.injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class ContentActionClient(base_action_client.BaseActionClient):

    def _get_libset(self):
        self.yum_repo_action_invoker = repolib.RepoActionInvoker()
        self.ostree_repo_action_invoker = ostree_action_invoker.OstreeRepoActionInvoker()

        plugin_manager = inj.require(inj.PLUGIN_MANAGER)

        content_action_class_list = []

        log.debug("cacl: %s" % content_action_class_list)
        plugin_manager.run('content_plugin_search',
                            content_action_class_list=content_action_class_list)

        log.debug("post cacl: %s" % content_action_class_list)

        lib_set = [self.yum_repo_action_invoker,
                   self.ostree_repo_action_invoker]

        for content_action_class in content_action_class_list:
            content_action = content_action_class()
            lib_set.append(content_action)

        return lib_set
