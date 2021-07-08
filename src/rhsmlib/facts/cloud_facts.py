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
import json

from cloud_what.provider import get_cloud_provider
from rhsmlib.facts import collector


log = logging.getLogger(__name__)


class CloudFactsCollector(collector.FactsCollector):
    """
    Class used for collecting facts related to Cloud instances
    """

    def __init__(self, arch=None, prefix=None, testing=None, collected_hw_info=None):
        super(CloudFactsCollector, self).__init__(
            arch=arch,
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )

        self.hardware_methods = []

        # Try to detect cloud provider
        self.cloud_provider = get_cloud_provider(self._collected_hw_info)
        if self.cloud_provider is not None:
            # Create dispatcher for supported cloud providers
            cloud_provider_dispatcher = {
                "aws": self.get_aws_facts,
                "azure": self.get_azure_facts,
                "gcp": self.get_gcp_facts
            }
            # Set method according detected cloud provider
            if self.cloud_provider.CLOUD_PROVIDER_ID in cloud_provider_dispatcher:
                self.hardware_methods = [
                    cloud_provider_dispatcher[self.cloud_provider.CLOUD_PROVIDER_ID]
                ]

    def get_aws_facts(self):
        """
        Try to get AWS facts (only instance ID ATM) of machine running on AWS public cloud
        :return: dictionary containing {"aws_instance_id": some_instance_ID}, when the machine is able to gather
            metadata from AWS cloud provider; otherwise returns empty dictionary {}
        """

        metadata_str = self.cloud_provider.get_metadata()

        facts = {}
        if metadata_str is not None:
            values = self.parse_json_content(metadata_str)

            # Add these three attributes to system facts
            if 'instanceId' in values:
                facts['aws_instance_id'] = values['instanceId']

            if 'accountId' in values:
                facts['aws_account_id'] = values['accountId']

            # BTW: There should be only two types of billing codes: bp-63a5400a and bp-6fa54006 in the list,
            # when RHEL is used. When the subscription-manager is used by some other Linux distribution,
            # then there could be different codes or it could be null
            if 'billingProducts' in values:
                billing_products = values['billingProducts']
                if isinstance(billing_products, list):
                    facts['aws_billing_products'] = " ".join(billing_products)
                elif billing_products is None:
                    facts['aws_billing_products'] = billing_products
                else:
                    log.debug('AWS metadata attribute billingProducts has to be list or null')

            if 'marketplaceProductCodes' in values:
                marketplace_product_codes = values['marketplaceProductCodes']
                if isinstance(marketplace_product_codes, list):
                    facts['aws_marketplace_product_codes'] = " ".join(marketplace_product_codes)
                elif marketplace_product_codes is None:
                    facts['aws_marketplace_product_codes'] = marketplace_product_codes
                else:
                    log.debug('AWS metadata attribute marketplaceProductCodes has to be list or null')

        return facts

    def get_azure_facts(self):
        """
        Try to get facts of VM running on Azure public cloud. Returned dictionary has following format:
            {
                "azure_instance_id": some_instance_ID,
                "azure_offer": some_offer,
                "azure_sku": some_sku
            }
        :return: dictionary containing Azure facts, when the machine is able to gather metadata
            from Azure cloud provider; otherwise returns empty dictionary {}
        """

        metadata_str = self.cloud_provider.get_metadata()

        facts = {}
        if metadata_str is not None:
            values = self.parse_json_content(metadata_str)
            if 'compute' in values:
                if 'vmId' in values['compute']:
                    facts["azure_instance_id"] = values['compute']['vmId']
                if 'sku' in values['compute']:
                    facts['azure_sku'] = values['compute']['sku']
                if 'offer' in values['compute']:
                    facts['azure_offer'] = values['compute']['offer']
        return facts

    def get_gcp_facts(self):
        """
        Try to get facts of VM running on GCP public cloud. Only instance_id is reported ATM.
        :return: dictionary containing GCP facts, when the machine is able to gather metadata
            from GCP cloud provider; otherwise returns empty dictionary {}
        """

        encoded_jwt_token = self.cloud_provider.get_metadata()

        facts = {}
        if encoded_jwt_token is not None:
            jose_header, metadata, signature = self.cloud_provider.decode_jwt(encoded_jwt_token)
            if metadata is not None:
                values = self.parse_json_content(metadata)
                if 'google' in values and \
                        'compute_engine' in values['google'] and \
                        'instance_id' in values['google']['compute_engine']:
                    facts = {
                        "gcp_instance_id": values['google']['compute_engine']['instance_id']
                    }
                else:
                    log.debug('GCP instance_id not found in JWT token')
        return facts

    @staticmethod
    def parse_json_content(content):
        """
        Parse content returned from AWS metadata provider
        :param content: string of JSON document
        :return: Dictionary containing values from parsed JSON document
        """
        try:
            return json.loads(content)
        except ValueError as e:
            raise ValueError('Failed to parse json data with error: %s', str(e))
