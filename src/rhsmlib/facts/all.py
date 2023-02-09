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
from typing import Dict, List, Union

from rhsmlib.facts import collector
from rhsmlib.facts import custom
from rhsmlib.facts import host_collector
from rhsmlib.facts import hwprobe
from rhsmlib.facts import insights
from rhsmlib.facts import kpatch
from rhsmlib.facts import cloud_facts
from rhsmlib.facts import pkg_arches
from rhsmlib.facts import network


class AllFactsCollector(collector.FactsCollector):
    def __init__(self):
        self.collectors: List[type(collector.FactsCollector)] = [
            collector.StaticFactsCollector,
            host_collector.HostCollector,
            hwprobe.HardwareCollector,
            network.NetworkCollector,
            custom.CustomFactsCollector,
            insights.InsightsCollector,
            kpatch.KPatchCollector,
            cloud_facts.CloudFactsCollector,
            pkg_arches.SupportedArchesCollector,
        ]

    def get_all(self) -> Dict[str, Union[str, int, bool, None]]:
        results: Dict[str, Union[str, int, bool, None]] = {}
        for fact_collector_cls in self.collectors:
            fact_collector: collector.FactsCollector = fact_collector_cls(collected_hw_info=results)
            results.update(fact_collector.get_all())
        return results
