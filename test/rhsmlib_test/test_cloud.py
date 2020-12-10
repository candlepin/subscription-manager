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
Module for testing Python all modules from Python package rhsmlib.cloud
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import patch, Mock

from rhsmlib.cloud.providers import aws, azure, gcp
from rhsmlib.cloud.utils import detect_cloud_provider


class TestAWSDetector(unittest.TestCase):
    """
    Class used for testing detector of AWS
    """

    def test_aws_not_vm(self):
        """
        Test for the case, when the machine is host (not virtual machine)
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': False,
            'dmi.bios.version': 'cool hardware company'
        }
        aws_detector = aws.AWSCloudDetector(facts)
        is_vm = aws_detector.is_vm()
        self.assertFalse(is_vm)

    def test_aws_vm_using_xen(self):
        """
        Test for the case, when the vm is running on AWS Xen
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'xen',
            'dmi.bios.version': 'amazon'
        }
        aws_detector = aws.AWSCloudDetector(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        is_aws_xen_vm = aws_detector.is_running_on_cloud()
        self.assertTrue(is_aws_xen_vm)

    def test_aws_vm_using_kvm(self):
        """
        Test for the case, when the vm is running on AWS KVM
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': '1.0',
            'dmi.bios.vendor': 'Amazon EC2'
        }
        aws_detector = aws.AWSCloudDetector(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        is_aws_kvm_vm = aws_detector.is_running_on_cloud()
        self.assertTrue(is_aws_kvm_vm)

    def test_vm_not_on_aws_cloud(self):
        """
        Test for the case, when the vm is not running on AWS
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': '1.0',
            'dmi.bios.vendor': 'Foo'
        }
        aws_detector = aws.AWSCloudDetector(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        is_aws_vm = aws_detector.is_running_on_cloud()
        self.assertFalse(is_aws_vm)

    def test_vm_without_dmi_bios_info(self):
        """
        Test for the case, when SM BIOS does not provide any useful information for our code
        """
        # We will mock facts using simple dictionary
        facts = {}
        aws_detector = aws.AWSCloudDetector(facts)
        is_vm = aws_detector.is_vm()
        self.assertFalse(is_vm)
        is_aws_vm = aws_detector.is_running_on_cloud()
        self.assertFalse(is_aws_vm)

    def test_vm_system_uuid_starts_with_ec2(self):
        """
        Test for the case, when system UUID starts with EC2 string as it is described here:
        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/identify_ec2_instances.html
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'dmi.system.uuid': 'EC2263F8-15F3-4A34-B186-FAD8AB963431'
        }
        aws_detector = aws.AWSCloudDetector(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        probability = aws_detector.is_likely_running_on_cloud()
        self.assertEqual(probability, 0.1)


class TestAzureDetector(unittest.TestCase):
    """
    Class used for testing detector of Azure
    """

    def test_azure_not_vm(self):
        """
        Test for the case, when the machine is host (not virtual machine)
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': False,
            'dmi.bios.version': 'cool hardware company'
        }
        azure_detector = azure.AzureCloudDetector(facts)
        is_vm = azure_detector.is_vm()
        self.assertFalse(is_vm)

    def test_azure_vm(self):
        """
        Test for the case, when the vm is running on Azure
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
            'dmi.bios.version': '090008',
            'dmi.chassis.asset_tag': '7783-7084-3265-9085-8269-3286-77'
        }
        azure_detector = azure.AzureCloudDetector(facts)
        is_vm = azure_detector.is_vm()
        self.assertTrue(is_vm)
        is_azure_vm = azure_detector.is_running_on_cloud()
        self.assertTrue(is_azure_vm)

    def test_vm_not_on_azure_cloud(self):
        """
        Test for the case, when the vm is not running on AWS
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
            'dmi.bios.version': '090008',
            'dmi.bios.vendor': 'Foo'
        }
        azure_detector = azure.AzureCloudDetector(facts)
        is_vm = azure_detector.is_vm()
        self.assertTrue(is_vm)
        is_azure_vm = azure_detector.is_running_on_cloud()
        self.assertFalse(is_azure_vm)

    def test_vm_without_dmi_bios_info(self):
        """
        Test for the case, when MS BIOS does not provide any useful information for our code
        """
        # We will mock facts using simple dictionary
        facts = {}
        azure_detector = azure.AzureCloudDetector(facts)
        is_vm = azure_detector.is_vm()
        self.assertFalse(is_vm)
        is_azure_vm = azure_detector.is_running_on_cloud()
        self.assertFalse(is_azure_vm)


class TestGCPDetector(unittest.TestCase):
    """
    Class used for testing detector of GCP
    """

    def test_gcp_not_vm(self):
        """
        Test for the case, when the machine is host (not virtual machine)
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': False,
            'dmi.bios.version': 'cool hardware company'
        }
        gcp_detector = gcp.GCPCloudDetector(facts)
        is_vm = gcp_detector.is_vm()
        self.assertFalse(is_vm)

    def test_gcp_vm(self):
        """
        Test for the case, when the vm is running on GCP
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': 'Google',
            'dmi.bios.vendor': 'Google'
        }
        gcp_detector = gcp.GCPCloudDetector(facts)
        is_vm = gcp_detector.is_vm()
        self.assertTrue(is_vm)
        is_gcp_vm = gcp_detector.is_running_on_cloud()
        self.assertTrue(is_gcp_vm)

    def test_vm_not_on_gcp_cloud(self):
        """
        Test for the case, when the vm is not running on GCP
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': '1.0',
            'dmi.bios.vendor': 'Foo'
        }
        gcp_detector = gcp.GCPCloudDetector(facts)
        is_vm = gcp_detector.is_vm()
        self.assertTrue(is_vm)
        is_gcp_vm = gcp_detector.is_running_on_cloud()
        self.assertFalse(is_gcp_vm)


class TestCloudUtils(unittest.TestCase):
    """
    Class for testing rhsmlib.cloud.utils module
    """
    def setUp(self):
        """
        Set up two mocks that are used in all tests
        """
        host_collector_patcher = patch('rhsmlib.cloud.utils.HostCollector')
        self.host_collector_mock = host_collector_patcher.start()
        self.host_fact_collector_instance = Mock()
        self.host_collector_mock.return_value = self.host_fact_collector_instance
        self.addCleanup(host_collector_patcher.stop)

        hardware_collector_patcher = patch('rhsmlib.cloud.utils.HardwareCollector')
        self.hardware_collector_mock = hardware_collector_patcher.start()
        self.hw_fact_collector_instance = Mock()
        self.hardware_collector_mock.return_value = self.hw_fact_collector_instance
        self.addCleanup(hardware_collector_patcher.stop)

    def test_detect_cloud_provider_aws(self):
        """
        Test the case, when detecting of aws works as expected
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'Amazon EC2'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['aws'])

    def test_detect_cloud_provider_aws_heuristics(self):
        """
        Test the case, when detecting of aws does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'AWS',
            'dmi.bios.version': '1.0'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['aws', 'gcp'])

    def test_detect_cloud_provider_gcp(self):
        """
        Test the case, when detecting of gcp works as expected
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'Google',
            'dmi.bios.version': 'Google'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['gcp'])

    def test_detect_cloud_provider_gcp_heuristics(self):
        """
        Test the case, when detecting of gcp does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'Foo Company',
            'dmi.bios.version': '1.0',
            'dmi.chassis.asset_tag': 'Google Cloud'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['gcp', 'aws'])

    def test_detect_cloud_provider_azure(self):
        """
        Test the case, when detecting of azure works as expected
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
        }
        hw_facts = {
            'dmi.bios.vendor': 'Foo company',
            'dmi.bios.version': '1.0',
            'dmi.chassis.asset_tag': '7783-7084-3265-9085-8269-3286-77'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['azure'])

    def test_detect_cloud_provider_azure_heuristics(self):
        """
        Test the case, when detecting of azure does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
        }
        hw_facts = {
            'dmi.bios.vendor': 'Microsoft',
            'dmi.bios.version': '1.0',
            'dmi.system.manufacturer': 'Google',
            'dmi.chassis.manufacturer': 'Amazon'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['azure', 'gcp', 'aws'])
