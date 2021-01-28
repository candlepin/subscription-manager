from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import socket
import mock

from rhsmlib.facts import cloud_facts
from rhsm.https import httplib
from mock import patch


from subscription_manager import injection as inj

AWS_INSTANCE_ID = "i-2d05f031d20c"
CLOUD_INSTANCE_ID = "i-1d06f031e20c"
CACHED_AWS_INSTANCE_ID = "i-2e05a031e20d"


class TestInsightsCollector(unittest.TestCase):
    def setUp(self):
        super(TestInsightsCollector, self).setUp()
        self.mock_facts = mock.Mock()
        inj.provide(inj.FACTS, self.mock_facts)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_instance_id(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {}
        MockConn.return_value.getresponse.return_value.read.return_value = \
            '{"privateIp": "10.158.112.84", \
            "version" : "2017-09-30", \
            "instanceId" : "' + AWS_INSTANCE_ID + '"}'
        facts = self.collector.get_all()
        self.assertIn("aws_instance_id", facts)
        self.assertEqual(facts["aws_instance_id"], AWS_INSTANCE_ID)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_not_aws_instance(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "1.0.cloud"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {}
        MockConn.return_value.getresponse.return_value.read.return_value = \
            "{'privateIp' : '10.158.112.84', \
            'version' : '2017-09-30, \
            'instanceId' : '" + CLOUD_INSTANCE_ID + "'}"
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_not_instance_id(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {}
        MockConn.return_value.getresponse.return_value.read.return_value = \
            "{'privateIp' : '10.158.112.84', \
            'version' : '2017-09-30'}"
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    # test ensures that exception is captured and does not impede
    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_bad_json(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {}
        MockConn.return_value.getresponse.return_value.read.return_value = \
            "other text stuff"
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    # test ensures that exception is captured and does not impede
    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_timeout(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {}
        MockConn.return_value.getresponse.side_effect = socket.timeout
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    # test ensures that exception is captured and does not impede
    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_http_error(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {}
        MockConn.return_value.getresponse.side_effect = httplib.HTTPException(mock.Mock(return_value={'status': 500}), 'error')
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_instance_id_from_cache(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        self.mock_facts.return_value.read_cache_only.return_value = {"aws_instance_id": CACHED_AWS_INSTANCE_ID}
        # does not get read if in cache already
        MockConn.return_value.getresponse.return_value.read.return_value = \
            '{"privateIp": "10.158.112.84", \
            "version" : "2017-09-30", \
            "instanceId" : "' + AWS_INSTANCE_ID + '"}'
        facts = self.collector.get_all()
        self.assertIn("aws_instance_id", facts)
        self.assertEqual(facts["aws_instance_id"], CACHED_AWS_INSTANCE_ID)
