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

    DEFAULT_INSIGHTS_MACHINE_ID = "/etc/redhat-access-insights/machine-id"

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

        if insights_constants is not None:
            machine_id_filepath = insights_constants.machine_id_file
        else:
            machine_id_filepath = self.DEFAULT_INSIGHTS_MACHINE_ID

        try:
            with open(machine_id_filepath, "r") as fd:
                machine_id = fd.read()
        except IOError as err:
            log.debug("Unable to read insights machine_id file: %s, error: %s" % (machine_id_filepath, err))
        else:
            insights_id = {
                "insights_id": machine_id
            }

        return insights_id
