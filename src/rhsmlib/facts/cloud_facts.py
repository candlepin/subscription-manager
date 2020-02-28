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

from rhsmlib.facts import collector
from rhsm.https import httplib


log = logging.getLogger(__name__)

AWS_INSTANCE_URL = "169.254.169.254"
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
        values = {}
        if not self._collected_hw_info['dmi.bios.version'].find('amazon') >= 0:
            return ""
        facts_cache = inj.require(inj.FACTS).read_cache_only() or {}
        if 'aws_instance_id' in facts_cache:
            return {'aws_instance_id': facts_cache['aws_instance_id']}

        try:
            conn = httplib.HTTPConnection(AWS_INSTANCE_URL, timeout=AWS_INSTANCE_TIMEOUT)
            conn.request('GET', '/latest/dynamic/instance-identity/document')
            response = conn.getresponse()
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

    def parse_content(self, content):
        try:
            doc_values = json.loads(content)
            return doc_values
        except ValueError as e:
            raise ValueError('Failed to parse json data with error: %s', str(e))
