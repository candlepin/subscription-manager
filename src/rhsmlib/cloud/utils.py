# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Red Hat, Inc.
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

"""
This module contains several utils used for VMs running on clouds
"""

import logging

from rhsmlib.facts.host_collector import HostCollector
from rhsmlib.facts.hwprobe import HardwareCollector

from rhsmlib.cloud.providers.aws import AWSCloudDetector
from rhsmlib.cloud.providers.azure import AzureCloudDetector
from rhsmlib.cloud.providers.gcp import GCPCloudDetector

# List of classes with supported cloud providers
CLOUD_DETECTORS = [
    AWSCloudDetector,
    AzureCloudDetector,
    GCPCloudDetector
]

log = logging.getLogger(__name__)


def detect_cloud_provider():
    """
    This method tries to detect cloud provider using hardware information provided by dmidecode.
    When there is strong sign that the VM is running on one of the cloud provider, then return
    list containing only one provider. When there is no strong sign of one cloud provider, then
    try to detect cloud provider using heuristics methods. In this case this method will return
    list of all cloud providers sorted according detected probability
    :return: List of string representing detected cloud providers. E.g. ['aws'] or ['aws', 'gcp']
    """

    # Gather only information about hardware and virtualization
    facts = {}
    facts.update(HostCollector().get_all())
    facts.update(HardwareCollector().get_all())

    cloud_detectors = [cls(facts) for cls in CLOUD_DETECTORS]

    log.debug('Trying to detect cloud provider')

    # First try to detect cloud providers using strong signs
    cloud_list = []
    for cloud_detector in cloud_detectors:
        cloud_detected = cloud_detector.is_running_on_cloud()
        if cloud_detected is True:
            cloud_list.append(cloud_detector.ID)

    # When only one cloud provider was detected, then return the list with
    # one cloud provider. Print error in other cases and try to detect cloud providers
    # using heuristics methods
    if len(cloud_list) == 1:
        return cloud_list
    elif len(cloud_list) == 0:
        log.error('No cloud provider detected using strong signs')
    elif len(cloud_list) > 1:
        log.error('More than one cloud provider detected using strong signs ({providers})'.format(
            providers=", ".join(cloud_list)
        ))

    # When no cloud provider detected using strong signs, because behavior of cloud providers
    # has changed, then try to detect cloud provider using some heuristics
    cloud_list = []
    for cloud_detector in cloud_detectors:
        probability = cloud_detector.is_likely_running_on_cloud()
        if probability > 0.0:
            cloud_list.append((probability, cloud_detector.ID))
    # Sort list according probability (provider with highest probability first)
    cloud_list.sort(reverse=True)
    # We care only about order, not probability in the result (filter probability out)
    cloud_list = [item[1] for item in cloud_list]

    if len(cloud_list) == 0:
        log.error('No cloud provider detected using heuristics')

    return cloud_list


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src:./syspurse/src python3 -m rhsmlib.cloud.utils
if __name__ == '__main__':
    _result = detect_cloud_provider()
    print('>>> debug <<< result: %s' % _result)
