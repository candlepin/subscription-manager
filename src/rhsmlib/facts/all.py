from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
from rhsmlib.facts import collector
from rhsmlib.facts import custom
from rhsmlib.facts import host_collector
from rhsmlib.facts import hwprobe
from rhsmlib.facts import insights


class AllFactsCollector(collector.FactsCollector):
    def __init__(self):
        self.collectors = [
            collector.StaticFactsCollector(),
            host_collector.HostCollector(),
            hwprobe.HardwareCollector(),
            custom.CustomFactsCollector(),
            insights.InsightsCollector()
        ]

    def get_all(self):
        results = {}
        for fact_collector in self.collectors:
            results.update(fact_collector.get_all())
        return results
