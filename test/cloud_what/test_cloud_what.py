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
Unit testing of public part of cloud_what
"""

import unittest
from mock import patch, Mock

from cloud_what.providers import aws, azure, gcp
from cloud_what.provider import detect_cloud_provider, get_cloud_provider, DetectionMethod


class TestCloudProvider(unittest.TestCase):
    """
    Class for testing cloud_what.utils module
    """

    def setUp(self):
        """
        Set up two mocks that are used in all tests
        """
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

        custom_facts_collector_patcher = patch("cloud_what.provider.CustomFactsCollector")
        self.custom_facts_collector_mock = custom_facts_collector_patcher.start()
        self.custom_facts_collector_instance = Mock()
        self.custom_facts_collector_instance.get_all = Mock(return_value={})
        self.custom_facts_collector_mock.return_value = self.custom_facts_collector_instance
        self.addCleanup(custom_facts_collector_patcher.stop)

        host_collector_patcher = patch("cloud_what.provider.HostCollector")
        self.host_collector_mock = host_collector_patcher.start()
        self.host_fact_collector_instance = Mock()
        self.host_collector_mock.return_value = self.host_fact_collector_instance
        self.addCleanup(host_collector_patcher.stop)

        # hardware_collector_patcher = patch('cloud_what.provider.HardwareCollector')
        # self.hardware_collector_mock = hardware_collector_patcher.start()
        # self.hw_fact_collector_instance = Mock()
        # self.hardware_collector_mock.return_value = self.hw_fact_collector_instance
        # self.addCleanup(hardware_collector_patcher.stop)

        write_cache_patcher = patch("cloud_what.providers.aws.AWSCloudProvider._write_token_to_cache_file")
        self.write_cache_mock = write_cache_patcher.start()
        self.addCleanup(write_cache_patcher.stop)

        self.requests_patcher = patch("cloud_what._base_provider.requests")
        self.azure_requests_mock = self.requests_patcher.start()
        self.addCleanup(self.requests_patcher.stop)

    def tearDown(self):
        """
        Clean after each unit test
        """
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

    def test_detect_cloud_provider_aws(self):
        """
        Test the case, when detecting of aws works as expected
        """
        host_facts = {"virt.is_guest": True, "virt.host_type": "kvm", "dmi.bios.vendor": "Amazon EC2"}
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["aws"])

    def test_detect_cloud_provider_only_strong_signs(self):
        """
        Test the case, when detecting of aws does not work using strong signs, but detecting
        using only strong signs is requested
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "AWS",
            "dmi.bios.version": "1.0",
            "dmi.system.manufacturer": "Amazon",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider(methods=DetectionMethod.STRONG)
        self.assertEqual(detected_clouds, [])

    def test_detection_influenced_by_custom_facts(self):
        """
        When file with custom fact is set, then detection of cloud provider
        should be influenced by custom facts
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "Amazon EC2",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        # Following custom facts should override host_facts
        custom_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.vendor": "Microsoft",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
        }
        self.custom_facts_collector_instance.get_all.return_value = custom_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["azure"])

    def test_detect_cloud_provider_aws_heuristics(self):
        """
        Test the case, when detecting of aws does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "AWS",
            "dmi.bios.version": "1.0",
            "dmi.system.manufacturer": "Amazon",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["aws"])

    def test_detect_cloud_provider_gcp(self):
        """
        Test the case, when detecting of gcp works as expected
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "Google",
            "dmi.bios.version": "Google",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["gcp"])

    def test_detect_cloud_provider_gcp_heuristics(self):
        """
        Test the case, when detecting of gcp does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "Foo Company",
            "dmi.bios.version": "1.0",
            "dmi.chassis.asset_tag": "Google Cloud",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["gcp"])

    def test_detect_cloud_provider_azure(self):
        """
        Test the case, when detecting of azure works as expected
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.vendor": "Microsoft",
            "dmi.bios.version": "1.0",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["azure"])

    @patch("cloud_what.providers.azure.AzureCloudProvider._has_azure_linux_agent", Mock(return_value=True))
    def test_detect_cloud_provider_azure_with_dmidecode(self):
        """
        Test the case, when detecting of azure with dmidecode and azure linux agent works as expected
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.vendor": "Microsoft",
            "dmi.bios.version": "1.0",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["azure"])

    @patch("cloud_what.providers.azure.AzureCloudProvider._has_azure_linux_agent", Mock(return_value=True))
    def test_detect_cloud_provider_azure_without_dmidecode(self):
        """
        Test the case, when detecting of azure without dmidecode but with azure linux agent works as expected
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["azure"])

    @patch("cloud_what.providers.azure.AzureCloudProvider._has_azure_linux_agent", Mock(return_value=True))
    def test_detect_cloud_provider_azure_heuristics_with_azure_linux_agent(self):
        """
        Test the case, when detecting of azure does not work using strong signs, but it is necessary
        to use heuristics method. Azure linux agent exists.
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.vendor": "Microsoft",
            "dmi.bios.version": "1.0",
            "dmi.system.manufacturer": "Google",
            "dmi.chassis.manufacturer": "Amazon",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["azure"])

    @patch("cloud_what.providers.azure.AzureCloudProvider._has_azure_linux_agent", Mock(return_value=False))
    def test_detect_cloud_provider_azure_heuristics_without_azure_linux_agent(self):
        """
        Test the case, when detecting of azure does not work using strong signs and without azure linux agent
        to use heuristics method
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.vendor": "Microsoft",
            "dmi.bios.version": "1.0",
            "dmi.system.manufacturer": "Google",
            "dmi.chassis.manufacturer": "Amazon",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ["azure"])

    @patch("cloud_what.providers.azure.AzureCloudProvider._has_azure_linux_agent", Mock(return_value=True))
    def test_conclict_in_strong_signs_with_azure_linux_agent(self):
        """
        Test the case, when cloud providers change strong signs and there is conflict (two providers
        are detected using strong signs). In such case result using strong signs should be dropped
        and heuristics should be used, because strong signs do not work with probability and original
        order is influenced by the order of classes in 'constant' CLOUD_DETECTORS.
        Azure Linux Agent exists.
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "Google",
            "dmi.bios.version": "Amazon EC2",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
            "dmi.chassis.manufacturer": "Microsoft",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        detected_clouds.sort()
        self.assertEqual(detected_clouds, ["aws", "azure", "gcp"])

    @patch("cloud_what.providers.azure.AzureCloudProvider._has_azure_linux_agent", Mock(return_value=False))
    def test_conclict_in_strong_signs_without_azure_linux_agent(self):
        """
        Test the case, when cloud providers change strong signs and there is conflict (two providers
        are detected using strong signs). In such case result using strong signs should be dropped
        and heuristics should be used, because strong signs do not work with probability and original
        order is influenced by the order of classes in 'constant' CLOUD_DETECTORS.
        Azure Linux Agent does not exist.
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.vendor": "Google",
            "dmi.bios.version": "Amazon EC2",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
            "dmi.chassis.manufacturer": "Microsoft",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        detected_clouds.sort()
        self.assertEqual(detected_clouds, ["aws", "azure", "gcp"])

    def test_conclict_in_heuristics_detection(self):
        """
        Test the case, when cloud providers two cloud providers were
        detected using heuristics with same probability.
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.system.manufacturer": "Google",
            "dmi.chassis.manufacturer": "Amazon EC2",
        }

        aws_cloud_provider = aws.AWSCloudProvider(host_facts)
        azure_cloud_provider = azure.AzureCloudProvider(host_facts)
        gcp_cloud_provider = gcp.GCPCloudProvider(host_facts)

        probability_aws = aws_cloud_provider.is_likely_running_on_cloud()
        self.assertEqual(probability_aws, 0.6)
        probability_azure = azure_cloud_provider.is_likely_running_on_cloud()
        self.assertEqual(probability_azure, 0.0)
        probability_gcp = gcp_cloud_provider.is_likely_running_on_cloud()
        self.assertEqual(probability_gcp, 0.6)

        self.host_fact_collector_instance.get_all.return_value = host_facts
        detected_clouds = detect_cloud_provider()
        detected_clouds.sort()
        self.assertEqual(detected_clouds, ["aws", "gcp"])

    def test_get_cloud_provider(self):
        """
        Test getting instance of cloud provider
        """
        host_facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.vendor": "Microsoft",
            "dmi.bios.version": "1.0",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        cloud_provider = get_cloud_provider()
        self.assertIsInstance(cloud_provider, azure.AzureCloudProvider)
