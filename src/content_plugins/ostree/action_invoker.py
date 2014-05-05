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

from subscription_manager import certlib


class OstreeContentActionInvoker(object):
    def __init__(self):
        self.report = None

    def update(self):
        print "ostree content update"


class OstreeContentUpdateActionCommand(object):
    """UpdateActionCommand for ostree repos.

    Update the repo configuration for rpm-ostree when triggered.

    Return a OstreeContentUpdateReport.
    """
    def __init__(self):
        self.report = OstreeContentUpdateActionReport()


class OstreeContentUpdateActionReport(certlib.ActionReport):
    """Report class for reporting ostree content repo updates."""

    def __init__(self):
        super(OstreeContentUpdateActionReport, self).__init__()
