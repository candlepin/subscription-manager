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
import socket

from rhsmlib.facts import collector
from rhsm.https import httplib


log = logging.getLogger(__name__)

AWS_INSTANCE_IP = "169.254.169.254"
AWS_INSTANCE_PATH = "/latest/dynamic/instance-identity/document"
AWS_INSTANCE_TOKEN_PATH = "/latest/api/token"
AWS_INSTANCE_TOKEN_TTL = 3600  # value is in seconds
AWS_INSTANCE_TIMEOUT = 5  # value is in seconds

AZURE_INSTANCE_IP = "169.254.169.254"
AZURE_API_VERSION = "2021-02-01"
AZURE_INSTANCE_PATH = "/metadata/instance?api-version=" + AZURE_API_VERSION
AZURE_INSTANCE_TIMEOUT = 5  # value is in seconds


class CloudFactsCollector(collector.FactsCollector):
    """
    Class used for collecting facts related to Cloud instances
    """

    HEADERS = {
        'User-Agent': 'RHSM/1.0',
    }

    def __init__(self, arch=None, prefix=None, testing=None, collected_hw_info=None):
        super(CloudFactsCollector, self).__init__(
            arch=arch,
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )

        log.debug('Trying to detect public cloud')

        public_cloud = None
        if self.is_aws() is True:
            public_cloud = "aws"
            self.hardware_methods = [
                self.get_aws_facts
            ]

        if self.is_azure() is True:
            public_cloud = "azure"
            self.hardware_methods = [
                self.get_azure_facts
            ]

        if public_cloud is not None:
            log.debug('Detected public cloud: {public_cloud}'.format(public_cloud=public_cloud))

    def is_aws(self):
        """
        Is the VM running on AWS
        :return: True, when VM is running on AWS
        """
        hw_info = self._collected_hw_info

        if 'dmi.bios.version' in hw_info and 'amazon' in hw_info['dmi.bios.version']:
            return True

        if 'dmi.bios.vendor' in hw_info and 'Amazon EC2' in hw_info['dmi.bios.vendor']:
            return True

        return False

    def get_cloud_metadata(self, ip_addr, path, headers=None, timeout=5.0):
        """
        Try to get AWS metadata using only IMDSv1
        :return: http response
        """
        conn = httplib.HTTPConnection(ip_addr, timeout=timeout)
        if headers is None:
            headers = self.HEADERS
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        return response

    def get_aws_token(self, ip_addr, path, headers=None, timeout=5.0):
        """
        Try to get AWS token
        :return: AWS token or None, when it wasn't possible to get AWS token
        """
        log.debug('Trying to get AWS IMDSv2 token')
        token = None
        conn = httplib.HTTPConnection(ip_addr, timeout=timeout)
        if headers is None:
            headers = self.HEADERS
        try:
            conn.request('PUT', path, headers=headers)
            response = conn.getresponse()
            output = response.read()
            token = output.decode()
        except Exception as err:
            log.warning('Unable to get AWS token: {err}'.format(err=str(err)))
        else:
            log.debug('AWS token gathered')
        return token

    def get_aws_metadata(self):
        """
        Try to get AWS metadata using only IMDSv2, which is supported in all cases. Using of IMDSv1
        can be forbidden by administrator of VM on AWS console.
        :return: http response
        """

        # First try to get IMDSv2 token
        headers = {
            'X-aws-ec2-metadata-token-ttl-seconds': str(AWS_INSTANCE_TOKEN_TTL)
        }
        headers.update(self.HEADERS)
        token = self.get_aws_token(
            ip_addr=AWS_INSTANCE_IP,
            path=AWS_INSTANCE_TOKEN_PATH,
            headers=headers,
            timeout=AWS_INSTANCE_TIMEOUT
        )

        # When token is gathered, then try to get metadata using IMDSv2
        headers = {}
        if token is not None:
            headers = {
                'X-aws-ec2-metadata-token': token
            }
        headers.update(self.HEADERS)
        return self.get_cloud_metadata(
            ip_addr=AWS_INSTANCE_IP,
            path=AWS_INSTANCE_PATH,
            headers=headers,
            timeout=AWS_INSTANCE_TIMEOUT
        )

    def get_aws_facts(self):
        """
        Try to get facts from metadata returned by AWS IMDS server according this documentation:

        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/identify_ec2_instances.html

        :return: dictionary containing AWS facts or empty dictionary, when it wasn't
        possible to get information from IMDS server
        """
        log.debug('Trying to get AWS metadata')
        facts = {}
        try:
            response = self.get_aws_metadata()
            output = response.read()
            values = self.parse_content(output)
        except (httplib.HTTPException, ValueError, socket.timeout) as e:
            # Any exception is logged by value is simply not added.
            log.exception("Cannot retrieve AWS metadata: %s" % e)
        else:
            log.debug('AWS metadata gathered')
            if 'instanceId' in values:
                facts["aws_instance_id"] = values['instanceId']

            if 'accountId' in values:
                facts['aws_account_id'] = values['accountId']

            # Note: There should be only two types of billing codes: bp-63a5400a and bp-6fa54006 in the list,
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

    def is_azure(self):
        """
        Is VM running on Azure public cloud
        :return:
        """
        hw_info = self._collected_hw_info

        if 'dmi.chassis.asset_tag' in hw_info and \
                hw_info['dmi.chassis.asset_tag'] == '7783-7084-3265-9085-8269-3286-77':
            return True

        return False

    def get_azure_metadata(self):
        """
        Try to get AWS metadata using only IMDSv1
        :return: http response
        """
        headers = {
            "Metadata": "true",
        }
        headers.update(self.HEADERS)
        return self.get_cloud_metadata(
            ip_addr=AZURE_INSTANCE_IP,
            path=AZURE_INSTANCE_PATH,
            headers=headers,
            timeout=AZURE_INSTANCE_TIMEOUT
        )

    def get_azure_facts(self):
        """
        Try to get Azure facts from IMDS server according this documentation:

        https://docs.microsoft.com/en-us/azure/virtual-machines/linux/instance-metadata-service?tabs=linux#instance-metadata

        :return: dictionary containing AWS facts or empty dictionary, when it wasn't
        possible to get information from IMDS server
        """
        log.debug('Trying to get Azure metadata')
        facts = {}
        try:
            response = self.get_azure_metadata()
            output = response.read()
            values = self.parse_content(output)
        except (httplib.HTTPException, ValueError, socket.timeout) as e:
            # Any exception is logged by value is simply not added.
            log.exception("Cannot retrieve Azure metadata: %s" % e)
        else:
            log.debug('Azure metadata gathered')
            if 'compute' in values:
                if 'vmId' in values['compute']:
                    facts["azure_instance_id"] = values['compute']['vmId']
                if 'sku' in values['compute']:
                    facts['azure_sku'] = values['compute']['sku']
                if 'offer' in values['compute']:
                    facts['azure_offer'] = values['compute']['offer']
        return facts

    @staticmethod
    def parse_content(content):
        try:
            doc_values = json.loads(content)
            return doc_values
        except ValueError as e:
            raise ValueError('Failed to parse json data with error: %s', str(e))
