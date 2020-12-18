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
import subscription_manager.injection as inj

from rhsmlib.cloud.providers.aws import AWSCloudDetector
from rhsmlib.facts import collector
from rhsm.https import httplib


log = logging.getLogger(__name__)

AWS_INSTANCE_IP = "169.254.169.254"
AWS_INSTANCE_PATH = '/latest/dynamic/instance-identity/document'
AWS_INSTANCE_TIMEOUT = 5


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

        self.hardware_methods = [
            self.get_aws_instance_id
        ]

    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/identify_ec2_instances.html
    def get_aws_instance_id(self):
        """
        Try to get instance ID of machine running on AWS
        :return: dictionary containing {"aws_instance_id": some_instance_ID}, when the machine is running on
            AWS cloud; otherwise returns empty dictionary {}
        """
        values = {}

        # Is the machine running on VM and is it AWS?
        aws_cloud_detector = AWSCloudDetector(self._collected_hw_info)
        if aws_cloud_detector.is_running_on_cloud() is False:
            return {}

        # Try to read instance ID from cache first
        facts_cache = inj.require(inj.FACTS).read_cache_only() or {}
        if 'aws_instance_id' in facts_cache:
            return {'aws_instance_id': facts_cache['aws_instance_id']}

        # If the cache file does not include the instance ID, then try to
        # get instance ID from metadata provider
        try:
            response = self.get_aws_metadata()
            output = response.read()
            values = self.parse_content(output)
        except (httplib.HTTPException, ValueError, socket.timeout) as e:
            # any exception is logged by value is simply not added.
            log.exception("Cannot retrieve AWS instance Id: %s" % e)
        finally:
            if 'instanceId' in values:
                return {"aws_instance_id": values['instanceId']}
            else:
                return {}

    @staticmethod
    def get_aws_metadata():
        """
        Try to get AWS metadata
        :return: http response
        """
        conn = httplib.HTTPConnection(AWS_INSTANCE_IP, timeout=AWS_INSTANCE_TIMEOUT)
        conn.request('GET', AWS_INSTANCE_PATH)
        response = conn.getresponse()
        return response

    @staticmethod
    def parse_content(content):
        """
        Parse content returned from AWS metadata provider
        :param content: string of JSON document
        :return: Dictionary containing values from parsed JSON document
        """
        try:
            return json.loads(content)
        except ValueError as e:
            raise ValueError('Failed to parse json data with error: %s', str(e))
