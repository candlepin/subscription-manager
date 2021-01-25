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

# TODO: test Python3 syntax using flake8
# flake8: noqa

"""
This module contains several utils used for VMs running on clouds
"""

from typing import Union

import logging
import base64

from rhsmlib.facts.host_collector import HostCollector
from rhsmlib.facts.hwprobe import HardwareCollector
from rhsmlib.facts.custom import CustomFactsCollector

from rhsmlib.cloud.detector import CloudDetector
from rhsmlib.cloud.collector import CloudCollector

from rhsmlib.cloud.providers.aws import AWSCloudDetector, AWSCloudCollector
from rhsmlib.cloud.providers.azure import AzureCloudDetector, AzureCloudCollector
from rhsmlib.cloud.providers.gcp import GCPCloudDetector, GCPCloudCollector

# List of detector classes with supported cloud providers
CLOUD_DETECTORS = [
    AWSCloudDetector,
    AzureCloudDetector,
    GCPCloudDetector
]

# List of collector classes with supported cloud provider
CLOUD_COLLECTORS = [
    AWSCloudCollector,
    AzureCloudCollector,
    GCPCloudCollector
]

log = logging.getLogger(__name__)


def detect_cloud_provider() -> list:
    """
    This method tries to detect cloud provider using hardware information provided by dmidecode.
    When there is strong sign that the VM is running on one of the cloud provider, then return
    list containing only one provider. When there is no strong sign of one cloud provider, then
    try to detect cloud provider using heuristics methods. In this case this method will return
    list of all cloud providers sorted according detected probability
    :return: List of string representing detected cloud providers. E.g. ['aws'] or ['aws', 'gcp']
    """

    # Gather only information about hardware, virtualization and custom facts
    facts = {}
    facts.update(HostCollector().get_all())
    facts.update(HardwareCollector().get_all())
    # When cloud provider will change information provided by SM BIOS, then
    # customers will be able to create simple workaround using custom facts.
    facts.update(CustomFactsCollector().get_all())

    cloud_detectors = [cls(facts) for cls in CLOUD_DETECTORS]

    log.debug('Trying to detect cloud provider')

    # First try to detect cloud providers using strong signs
    cloud_list = []
    cloud_detector: CloudDetector
    for cloud_detector in cloud_detectors:
        cloud_detected = cloud_detector.is_running_on_cloud()
        if cloud_detected is True:
            cloud_list.append(cloud_detector.ID)

    # When only one cloud provider was detected, then return the list with
    # one cloud provider. Print error in other cases and try to detect cloud providers
    # using heuristics methods, because it will be necessary to sort the list according
    # probability
    if len(cloud_list) == 1:
        log.info('Detected one cloud provider using strong signs: {provider}'.format(provider=cloud_list[0]))
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
    cloud_detector: CloudDetector
    for cloud_detector in cloud_detectors:
        probability: float = cloud_detector.is_likely_running_on_cloud()
        if probability > 0.0:
            cloud_list.append((probability, cloud_detector.ID))
    # Sort list according probability (provider with highest probability first)
    cloud_list.sort(reverse=True)
    # We care only about order, not probability in the result (filter probability out)
    cloud_list = [item[1] for item in cloud_list]

    if len(cloud_list) == 0:
        log.error('No cloud provider detected using heuristics')
    else:
        log.info('Following list of cloud providers detected using heuristic: {providers}'.format(
            providers=", ".join(cloud_list)
        ))

    return cloud_list


def collect_cloud_info(cloud_list: list) -> dict:
    """
    Try to collect cloud information: metadata and signature provided by cloud provider.
    :param cloud_list: The list of detected cloud providers. In most cases the list contains only one item.
    :return: The dictionary with metadata and signature (when signature is provided by cloud provider).
        Empty dictionary is returned, when it wasn't possible to collect any metadata
    """

    # Create dispatcher dictionary from the list of supported cloud collectors
    cloud_collectors = {
        collector_cls.CLOUD_PROVIDER_ID: collector_cls for collector_cls in CLOUD_COLLECTORS
    }

    result = {}
    # Go through the list of detected cloud providers and try to collect
    # metadata. When metadata are gathered, then break the loop
    for cloud_collector_id in cloud_list:
        cloud_collector: CloudCollector = cloud_collectors[cloud_collector_id]()

        # Try to get metadata first
        metadata: Union[str, None] = cloud_collector.get_metadata()

        # When it wasn't possible to get metadata for this cloud provider, then
        # continue with next detected cloud provider
        if metadata is None:
            log.warning(f'No metadata gathered for cloud provider: {cloud_collector_id}')
            continue

        # Try to get signature
        signature: Union[str, None] = cloud_collector.get_signature()

        # When it is not possible to get signature for given cloud provider,
        # then silently set signature to empty string, because some cloud
        # providers does not provide signatures
        if signature is None:
            signature = ""

        log.info(f'Metadata and signature gathered for cloud provider: {cloud_collector_id}')

        # Encode metadata and signature using base64 encoding. Because base64.b64encode
        # returns values as bytes, then we decode it to string using ASCII encoding.
        b64_metadata: str = base64.b64encode(bytes(metadata, 'utf-8')).decode('ascii')
        b64_signature: str = base64.b64encode(bytes(signature, 'utf-8')).decode('ascii')

        result = {
            'cloud_id': cloud_collector_id,
            'metadata': b64_metadata,
            'signature': b64_signature
        }
        break

    return result


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src:./syspurse/src python3 -m rhsmlib.cloud.utils
if __name__ == '__main__':
    _result = detect_cloud_provider()
    print('>>> debug <<< result: %s' % _result)
