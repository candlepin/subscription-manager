#
# Copyright (c) 2011 - 2012 Red Hat, Inc.
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

import unittest

from rhsm.connection import ContentConnection, UEPConnection, drift_check, Restlib,\
    UnauthorizedException, ForbiddenException, AuthenticationException, RestlibException
import simplejson as json
import mock


class ConnectionTests(unittest.TestCase):

    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin",
                insecure=True)

        consumerInfo = self.cp.registerConsumer("test-consumer", "system", owner="admin")
        self.consumer_uuid = consumerInfo['uuid']

    def test_supports_resource(self):
        self.assertTrue(self.cp.supports_resource('consumers'))
        self.assertTrue(self.cp.supports_resource('admin'))
        self.assertFalse(self.cp.supports_resource('boogity'))

    def test_update_consumer_can_update_guests_with_empty_list(self):
        self.cp.updateConsumer(self.consumer_uuid, guest_uuids=[])

    def test_update_consumer_can_update_facts_with_empty_dict(self):
        self.cp.updateConsumer(self.consumer_uuid, facts={})

    def test_update_consumer_can_update_installed_products_with_empty_list(self):
        self.cp.updateConsumer(self.consumer_uuid, installed_products=[])

    def tearDown(self):
        self.cp.unregisterConsumer(self.consumer_uuid)


class BindRequestTests(unittest.TestCase):
    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin",
                insecure=True)

        consumerInfo = self.cp.registerConsumer("test-consumer", "system", owner="admin")
        self.consumer_uuid = consumerInfo['uuid']

    @mock.patch.object(Restlib,'validateResponse')
    @mock.patch('rhsm.connection.drift_check', return_value=False)
    @mock.patch('M2Crypto.httpslib.HTTPSConnection', auto_spec=True)
    def test_bind_no_args(self, mock_conn, mock_drift, mock_validate):

        self.cp.bind(self.consumer_uuid)

        # verify we called request() with kwargs that include 'body' as None
        # Specifically, we are checking that passing in "" to post_request, as
        # it does by default, results in None here. bin() passes no args there
        # so we use the default, "". See  bz #907536
        for (name, args, kwargs) in mock_conn.mock_calls:
            if name == '().request':
                self.assertEquals(None, kwargs['body'])

    @mock.patch.object(Restlib,'validateResponse')
    @mock.patch('rhsm.connection.drift_check', return_value=False)
    @mock.patch('M2Crypto.httpslib.HTTPSConnection', auto_spec=True)
    def test_bind_by_pool(self, mock_conn, mock_drift, mock_validate):
        # this test is just to verify we make the httplib connection with
        # right args, we don't validate the bind here
        self.cp.bindByEntitlementPool(self.consumer_uuid, '123121111', '1')
        for (name, args, kwargs) in mock_conn.mock_calls:
            if name == '().request':
                self.assertEquals(None, kwargs['body'])


class ContentConnectionTests(unittest.TestCase):

#    def setUp(self):
#        self.cc = ContentConnection(insecure=True)

    def testInsecure(self):
        ContentConnection(host="127.0.0.1", insecure=True)


class HypervisorCheckinTests(unittest.TestCase):

    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin",
                insecure=True)

    def test_hypervisor_checkin_can_pass_empty_map_and_updates_nothing(self):
        response = self.cp.hypervisorCheckIn("admin", "", {})

        self.assertEqual(len(response['failedUpdate']), 0)
        self.assertEqual(len(response['updated']), 0)
        self.assertEqual(len(response['created']), 0)


class RestlibTests(unittest.TestCase):

    def setUp(self):
        # Get handle to Restlib
        self.conn = UEPConnection().conn
        self.request_type = "GET"
        self.handler = "https://server/path"

    def _validate_response(self, response):
        # wrapper to specify request_type and handler
        return self.conn.validateResponse(response,
                                          request_type=self.request_type,
                                          handler=self.handler)

    def test_invalid_credentitals_thrown_on_401_with_empty_body(self):
        mock_response = {"status": 401}
        self.assertRaises(UnauthorizedException, self._validate_response,
                          mock_response)

    def test_standard_error_handling_on_401_with_defined_body(self):
        self._run_standard_error_handling_test(401)

    def test_invalid_credentitals_thrown_on_403_with_empty_body(self):
        mock_response = {"status": 403}
        self.assertRaises(ForbiddenException, self._validate_response,
                          mock_response)

    def test_standard_error_handling_on_403_with_defined_body(self):
        self._run_standard_error_handling_test(403)

    def _run_standard_error_handling_test(self, expected_error):
        expected_error = "My Expected Error."
        mock_response = {"status": expected_error,
                         "content": '{"displayMessage":"%s"}' % expected_error}

        try:
            self._validate_response(mock_response)
            self.fail("An exception should have been thrown.")
        except Exception, ex:
            self.assertTrue(isinstance(ex, RestlibException))
            self.assertEqual(expected_error, str(ex))
            self.assertEquals(expected_error, ex.code)
