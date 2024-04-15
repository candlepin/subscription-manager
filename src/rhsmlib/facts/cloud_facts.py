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
import json
from typing import Any, Dict, Callable, List, Optional, Union

from cloud_what._base_provider import BaseCloudProvider

from cloud_what.provider import get_cloud_provider, DetectionMethod
from rhsmlib.facts import collector


log = logging.getLogger(__name__)


class CloudFactsCollector(collector.FactsCollector):
    """
    Class used for collecting facts related to Cloud instances
    """

    def __init__(
        self,
        arch: str = None,
        prefix: str = None,
        testing: bool = None,
        collected_hw_info: Dict[str, Union[str, None]] = None,
    ):
        super(CloudFactsCollector, self).__init__(
            arch=arch,
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info,
        )

        self.hardware_methods: List[Callable] = []

        # Try to detect cloud provider using only strong method
        self.cloud_provider: Optional[BaseCloudProvider] = get_cloud_provider(
            facts=self._collected_hw_info,
            methods=DetectionMethod.STRONG,
        )

        if self.cloud_provider is not None:
            # Create dispatcher for supported cloud providers
            cloud_provider_dispatcher: Dict[str, Callable] = {
                "aws": self.get_aws_facts,
                "azure": self.get_azure_facts,
                "gcp": self.get_gcp_facts,
            }
            # Set method according detected cloud provider
            if self.cloud_provider.CLOUD_PROVIDER_ID in cloud_provider_dispatcher:
                self.hardware_methods: List[Callable] = [
                    cloud_provider_dispatcher[self.cloud_provider.CLOUD_PROVIDER_ID]
                ]

    def get_aws_facts(self) -> Dict[str, Union[str, None]]:
        """
        Try to get AWS facts (only instance ID ATM) of machine running on AWS public cloud
        :return:
            dictionary containing {"aws_instance_id": some_instance_ID} when
            the machine is able to gather metadata from AWS cloud provider;
            otherwise returns empty dictionary {}
        """

        metadata_str: str = self.cloud_provider.get_metadata()

        facts: Dict[str, Union[str, None]] = {}
        if metadata_str is not None:
            values: Dict[str, Union[str, None]] = self.parse_json_content(metadata_str)

            # Add these three attributes to system facts
            if "instanceId" in values:
                facts["aws_instance_id"] = values["instanceId"]

            if "accountId" in values:
                facts["aws_account_id"] = values["accountId"]

            # BTW: There should be only two types of billing codes: bp-63a5400a and bp-6fa54006 in the list,
            # when RHEL is used. When the subscription-manager is used by some other Linux distribution,
            # then there could be different codes, or it could be null
            if "billingProducts" in values:
                billing_products: Optional[List[str]] = values["billingProducts"]
                if isinstance(billing_products, list):
                    facts["aws_billing_products"] = " ".join(billing_products)
                elif billing_products is None:
                    facts["aws_billing_products"] = billing_products
                else:
                    log.debug("AWS metadata attribute billingProducts has to be list or null")

            if "marketplaceProductCodes" in values:
                marketplace_product_codes = values["marketplaceProductCodes"]
                if isinstance(marketplace_product_codes, list):
                    facts["aws_marketplace_product_codes"] = " ".join(marketplace_product_codes)
                elif marketplace_product_codes is None:
                    facts["aws_marketplace_product_codes"] = marketplace_product_codes
                else:
                    log.debug("AWS metadata attribute marketplaceProductCodes has to be list or null")

            if "instanceType" in values:
                facts["aws_instance_type"] = values["instanceType"]

            if "region" in values:
                facts["aws_region"] = values["region"]

        return facts

    def get_azure_facts(self) -> Dict[str, str]:
        """
        Try to get facts of VM running on Azure public cloud. Returned dictionary has the following format:
            {
                "azure_instance_id": some_instance_ID,
                "azure_offer": some_offer,
                "azure_sku": some_sku,
                "azure_subscription_id": some_subscription_ID
                "azure_location: azure region the VM is running in
            }
        :return: dictionary containing Azure facts, when the machine is able to gather metadata
            from Azure cloud provider; otherwise returns empty dictionary {}
        """

        metadata_str: str = self.cloud_provider.get_metadata()

        facts: Dict[str, str] = {}
        if metadata_str is not None:
            values: Dict[str, Any] = self.parse_json_content(metadata_str)
            if "compute" in values:
                if "vmId" in values["compute"]:
                    facts["azure_instance_id"] = values["compute"]["vmId"]
                if "sku" in values["compute"]:
                    facts["azure_sku"] = values["compute"]["sku"]
                if "offer" in values["compute"]:
                    facts["azure_offer"] = values["compute"]["offer"]
                if "subscriptionId" in values["compute"]:
                    facts["azure_subscription_id"] = values["compute"]["subscriptionId"]
                if "location" in values["compute"]:
                    facts["azure_location"] = values["compute"]["location"]
                if "extendedLocation" in values["compute"]:
                    if "name" in values["compute"]["extendedLocation"]:
                        facts["azure_extended_location_name"] = values["compute"]["extendedLocation"]["name"]
                    if "type" in values["compute"]["extendedLocation"]:
                        facts["azure_extended_location_type"] = values["compute"]["extendedLocation"]["type"]
        return facts

    def get_gcp_facts(self) -> Dict[str, str]:
        """
        Try to get facts of VM running on GCP public cloud. Only instance_id is reported ATM.
        :return: dictionary containing GCP facts, when the machine is able to gather metadata
            from GCP cloud provider; otherwise returns empty dictionary {}
        """

        encoded_jwt_token: str = self.cloud_provider.get_metadata()

        facts: Dict[str, str] = {}
        if encoded_jwt_token is not None:
            jose_header, metadata, signature = self.cloud_provider.decode_jwt(encoded_jwt_token)
            if metadata is not None:
                values: Dict[str, Any] = self.parse_json_content(metadata)
                if "google" in values and "compute_engine" in values["google"]:
                    # ID of instance
                    if "instance_id" in values["google"]["compute_engine"]:
                        facts["gcp_instance_id"] = values["google"]["compute_engine"]["instance_id"]
                    else:
                        log.debug("GCP instance_id not found in JWT token")
                    # IDs of licenses
                    if "license_id" in values["google"]["compute_engine"]:
                        gcp_license_codes = values["google"]["compute_engine"]["license_id"]
                        facts["gcp_license_codes"] = " ".join(gcp_license_codes)
                    else:
                        log.debug("GCP license codes not found in JWT token")
                    # ID of project
                    if "project_id" in values["google"]["compute_engine"]:
                        facts["gcp_project_id"] = values["google"]["compute_engine"]["project_id"]
                    else:
                        log.debug("GCP project_id not found in JWT token")
                    # number of project
                    if "project_number" in values["google"]["compute_engine"]:
                        facts["gcp_project_number"] = values["google"]["compute_engine"]["project_number"]
                    else:
                        log.debug("GCP project_number not found in JWT token")
                    # zone where the machine is located
                    if "zone" in values["google"]["compute_engine"]:
                        facts["gcp_zone"] = values["google"]["compute_engine"]["zone"]
                    else:
                        log.debug("GCP zone not found in JWT token")
                else:
                    log.debug("GCP google.compute_engine on found in JWT token")
        return facts

    @staticmethod
    def parse_json_content(content: str) -> Dict[str, Any]:
        """
        Parse content returned from AWS metadata provider
        :param content: string of JSON document
        :return: Dictionary containing values from parsed JSON document
        """
        try:
            return json.loads(content)
        except ValueError as e:
            raise ValueError("Failed to parse json data with error: %s", str(e))
