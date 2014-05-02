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

log = logging.getLogger('rhsm-app.' + __name__)


class ContentActionClient(base_action_client.BaseActionClient):

    def _get_libset(self):
        self.yum_repo_action_invoker = repolib.RepoActionInvoker()

        lib_set = [self.yum_repo_action_invoker]
        return lib_set
