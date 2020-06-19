# -*- coding: utf-8 -*-

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

import logging

from rhsmlib.facts import collector

try:
    from insights_client import constants as insights_constants
except ImportError:
    insights_constants = None

log = logging.getLogger(__name__)


class InsightsCollector(collector.FactsCollector):
    """
    Class used for collecting facts related to Red Hat Access Insights
    """

    def __init__(self, arch=None, prefix=None, testing=None, collected_hw_info=None):
        super(InsightsCollector, self).__init__(
            arch=arch,
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )

        self.hardware_methods = [
            self.get_insights_machine_id
        ]

    def get_insights_machine_id(self):
        """
        Try to return content of insights machine_id (UUID)
        :return: dictionary containing insights_id, when machine_id file exist.
        Otherwise empty dictionary is returned.
        """
        insights_id = {}
        paths_to_check = [
            "/etc/insights-client/machine-id",  # should be the current known location
            "/etc/redhat-access-insights/machine-id",  # location prior to 3.0.13 of insights-client
        ]
        if insights_constants is not None and hasattr(insights_constants, 'machine_id_file'):
            paths_to_check.insert(0, insights_constants.machine_id_file)

        for filepath in paths_to_check:
            try:
                with open(filepath, "r") as fd:
                    machine_id = fd.read()
            except IOError as err:
                log.debug("Unable to read insights machine_id file: %s, error: %s" % (filepath, err))
            else:
                insights_id = {
                    "insights_id": machine_id
                }
                break

        return insights_id
