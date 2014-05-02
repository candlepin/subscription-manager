
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

from subscription_manager import certlib
#from subscription_manager import ostreelib

log = logging.getLogger('rhsm-app.' + __name__)


class OstreeRepoActionInvoker(certlib.BaseActionInvoker):
    """Invoker for ostree content repo config related actions."""
    def __init__(self):
        super(OstreeRepoActionInvoker, self).__init__()

    def _do_update(self):
        action = OstreeRepoUpdateActionCommand()
        return action.perform()


class OstreeRepoUpdateActionCommand(object):
    """Update rpm-ostree repo configuration."""
    def __init__(self):
        self.report = OstreeRepoUpdateActionReport()

    def perform(self):
        log.debug("Whee, update a ostree repo config!")


class OstreeRepoUpdateActionReport(certlib.ActionReport):
    name = "Ostree repo updates"
