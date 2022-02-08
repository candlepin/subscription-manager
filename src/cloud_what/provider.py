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
from rhsmlib.facts.custom import CustomFactsCollector

from cloud_what.providers.aws import AWSCloudProvider
from cloud_what.providers.azure import AzureCloudProvider
from cloud_what.providers.gcp import GCPCloudProvider


# List of classes with supported cloud providers
CLOUD_PROVIDERS = [
    AWSCloudProvider,
    AzureCloudProvider,
    GCPCloudProvider
]


log = logging.getLogger(__name__)


def gather_system_facts():
    """
    Try to gather system facts necessary for detection of cloud provider
    :return: Dictionary with system facts
    """
    facts = {}

    # Gather only basic information about hardware, virtualization and custom facts
    facts.update(HostCollector().get_all())

    # When cloud provider will change information provided by SM BIOS, then
    # customers will be able to create simple workaround using custom facts.
    facts.update(CustomFactsCollector().get_all())

    return facts


def _get_cloud_providers(facts=None, threshold=0.5):
    """
    This method tries to detect cloud providers and return list of possible cloud providers
    :param facts: Dictionary with system facts
    :param threshold: Threshold using for detection of cloud provider
    :return: List of cloud providers
    """
    if facts is None:
        facts = gather_system_facts()

    # Create instances of all supported cloud providers
    cloud_providers = [cls(facts) for cls in CLOUD_PROVIDERS]

    log.debug('Trying to detect cloud provider')

    # First try to detect cloud providers using strong signs
    cloud_list = []
    for cloud_provider in cloud_providers:
        cloud_detected = cloud_provider.is_running_on_cloud()
        if cloud_detected is True:
            cloud_list.append(cloud_provider)

    # When only one cloud provider was detected, then return this cloud provider
    # probability
    if len(cloud_list) == 1:
        log.debug('Detected one cloud provider using strong signs: {provider}'.format(
            provider=cloud_list[0].CLOUD_PROVIDER_ID)
        )
        return cloud_list, True
    elif len(cloud_list) == 0:
        log.debug('No cloud provider detected using strong signs')
    elif len(cloud_list) > 1:
        log.error('More than one cloud provider detected using strong signs ({providers})'.format(
            providers=", ".join([cloud_provider.CLOUD_PROVIDER_ID for cloud_provider in cloud_list])
        ))

    # When no cloud provider detected using strong signs, because behavior of cloud providers
    # has changed, then try to detect cloud provider using some heuristics
    cloud_list = []
    for cloud_provider in cloud_providers:
        probability = cloud_provider.is_likely_running_on_cloud()
        # We have to filter out VMs, where is low probability that it runs on public cloud,
        # because it would cause further attempts to contact IMDS servers of cloud providers.
        # Default value 0.5 was just estimated from observation of existing data returned
        # by cloud providers.
        log.debug('Cloud provider {} has probability: {}'.format(
            cloud_provider.CLOUD_PROVIDER_ID,
            probability
        ))
        if probability > threshold:
            cloud_list.append((probability, cloud_provider))
    # Sort list according only probability (provider with the highest probability first)
    cloud_list.sort(key=lambda x: x[0], reverse=True)
    # We care only about order, not probability in the result (filter probability out)
    cloud_list = [item[1] for item in cloud_list]

    if len(cloud_list) == 0:
        log.debug('No cloud provider detected using heuristics')
    else:
        log.debug('Following cloud providers detected using heuristics: {providers}'.format(
            providers=', '.join([cloud_provider.CLOUD_PROVIDER_ID for cloud_provider in cloud_list])
        ))

    return cloud_list, False


def get_cloud_provider(facts=None, threshold=0.5):
    """
    This method tries to detect cloud provider and return corresponding instance of
    cloud provider.
    :param facts: Dictionary with system facts
    :param threshold: Threshold used for heuristic detection of cloud provider
    :return: Instance of cloud provider or None
    """
    cloud_list, strong_sign = _get_cloud_providers(facts, threshold)

    # When only one cloud provider detected using strong signs, then it is not
    # necessary to try to gather metadata from cloud provider
    if len(cloud_list) == 1 and strong_sign is True:
        return cloud_list[0]

    if len(cloud_list) > 0:
        # Try to get metadata from cloud provider and return first cloud provider, which is
        # able to get metadata. Note: gathered metadata are cached in-memory. Thus another attempt
        # of gathering metadata will not hit server, but metadata will be read from in-memory cache.
        for cloud_provider in cloud_list:
            metadata = cloud_provider.get_metadata()
            if metadata is not None:
                log.info('Metadata gathered from cloud provider detected using heuristics: {provider}'.format(
                    provider=cloud_provider.CLOUD_PROVIDER_ID)
                )
                return cloud_provider

        log.debug('Unable to get metadata from any cloud provider detected using heuristics')

    return None


def detect_cloud_provider(facts=None, threshold=0.5):
    """
    This method tries to detect cloud provider using hardware information provided by dmidecode.
    When there is strong sign that the VM is running on one of the cloud provider, then return
    list containing only one provider. When there is no strong sign of one cloud provider, then
    try to detect cloud provider using heuristics methods. In this case this method will return
    list of all cloud providers sorted according detected probability
    :param facts: dictionary of facts. When no facts are provided, then hardware, virtualization
        and custom facts are gathered.
    :param threshold: Threshold used for heuristic detection of cloud provider
    :return: List of string representing detected cloud providers. E.g. ['aws'] or ['aws', 'gcp']
    """

    cloud_list, strong_sign = _get_cloud_providers(facts, threshold)

    # We care only about IDs of cloud providers in this method
    cloud_list = [cloud_provider.CLOUD_PROVIDER_ID for cloud_provider in cloud_list]

    return cloud_list


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src python3 -m cloud_what.provider
if __name__ == '__main__':
    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Try to detect cloud provider with facts provided by rhsmlib.facts
    _detector_result = detect_cloud_provider()
    print('>>> debug <<< detector result: {}'.format(_detector_result))
