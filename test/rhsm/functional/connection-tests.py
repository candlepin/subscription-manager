from __future__ import print_function, division, absolute_import

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

import os
import random
import string
import unittest

from nose.plugins.attrib import attr

from rhsm.connection import ContentConnection, UEPConnection, Restlib,\
    UnauthorizedException, ForbiddenException, RestlibException
from mock import patch


def random_string(name, target_length=32):
    ''' Returns a len 32 string starting with "name"'''
    for i in range(max(target_length - len(name), 0)):
        name += random.choice(string.ascii_lowercase)
    return name


@attr('functional')
class ConnectionTests(unittest.TestCase):

    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin", insecure=True)

        self.consumer = self.cp.registerConsumer("test-consumer", "system", owner="admin")
        self.consumer_uuid = self.consumer['uuid']

    def test_supports_resource(self):
        self.assertTrue(self.cp.supports_resource('consumers'))
        self.assertTrue(self.cp.supports_resource('admin'))
        self.assertFalse(self.cp.supports_resource('boogity'))

    def test_has_capability(self):
        self.cp.capabilities = ['cores', 'hypervisors_async']
        self.assertTrue(self.cp.has_capability('cores'))
        self.assertFalse(self.cp.has_capability('boogityboo'))

    def test_update_consumer_can_update_guests_with_empty_list(self):
        self.cp.updateConsumer(self.consumer_uuid, guest_uuids=[])

    def test_update_consumer_can_update_facts_with_empty_dict(self):
        self.cp.updateConsumer(self.consumer_uuid, facts={})

    def test_update_consumer_can_update_installed_products_with_empty_list(self):
        self.cp.updateConsumer(self.consumer_uuid, installed_products=[])

    def test_update_consumer_sets_hypervisor_id(self):
        testing_hypervisor_id = random_string("testHypervisor")
        self.cp.updateConsumer(self.consumer_uuid, hypervisor_id=testing_hypervisor_id)
        hypervisor_id = self.cp.getConsumer(self.consumer_uuid)['hypervisorId']
        # Hypervisor ID should be set and lower case
        expected = testing_hypervisor_id.lower()
        self.assertEqual(expected, hypervisor_id['hypervisorId'])

    def test_create_consumer_sets_hypervisor_id(self):
        testing_hypervisor_id = random_string("someId")
        consumerInfo = self.cp.registerConsumer("other-test-consumer",
                "system", owner="admin", hypervisor_id=testing_hypervisor_id)
        # Unregister before making assertions, that way it should always happen
        self.cp.unregisterConsumer(consumerInfo['uuid'])
        # Hypervisor ID should be set and lower case
        expected = testing_hypervisor_id.lower()
        self.assertEqual(expected, consumerInfo['hypervisorId']['hypervisorId'])

    def test_add_single_guest_id_string(self):
        testing_guest_id = random_string("guestid")
        self.cp.addOrUpdateGuestId(self.consumer_uuid, testing_guest_id)
        guestIds = self.cp.getGuestIds(self.consumer_uuid)
        self.assertEqual(1, len(guestIds))

    def test_add_single_guest_id(self):
        testing_guest_id = random_string("guestid")
        guest_id_object = {"guestId": testing_guest_id, "attributes": {"some attr": "some value"}}
        self.cp.addOrUpdateGuestId(self.consumer_uuid, guest_id_object)

        guestId = self.cp.getGuestId(self.consumer_uuid, testing_guest_id)

        # This check seems silly...
        self.assertEqual(testing_guest_id, guestId['guestId'])
        self.assertEqual('some value', guestId['attributes']['some attr'])

    def test_remove_single_guest_id(self):
        testing_guest_id = random_string("guestid")
        self.cp.addOrUpdateGuestId(self.consumer_uuid, testing_guest_id)
        guestIds = self.cp.getGuestIds(self.consumer_uuid)
        self.assertEqual(1, len(guestIds))

        # Delete the guestId
        self.cp.removeGuestId(self.consumer_uuid, testing_guest_id)

        # Check that no guestIds exist anymore
        guestIds = self.cp.getGuestIds(self.consumer_uuid)
        self.assertEqual(0, len(guestIds))

    def test_update_single_guest_id(self):
        testing_guest_id = random_string("guestid")
        guest_id_object = {"guestId": testing_guest_id, "attributes": {"some attr": "some value"}}
        self.cp.addOrUpdateGuestId(self.consumer_uuid, guest_id_object)
        guestId = self.cp.getGuestId(self.consumer_uuid, testing_guest_id)
        # check the guestId was created and has the expected attribute
        self.assertEqual('some value', guestId['attributes']['some attr'])

        guest_id_object['attributes']['some attr'] = 'crazy new value'
        self.cp.addOrUpdateGuestId(self.consumer_uuid, guest_id_object)
        guestId = self.cp.getGuestId(self.consumer_uuid, testing_guest_id)

        # Verify there's still only one guestId
        guestIds = self.cp.getGuestIds(self.consumer_uuid)
        self.assertEqual(1, len(guestIds))

        # Check that the attribute has changed
        self.assertEqual('crazy new value', guestId['attributes']['some attr'])

    def test_get_owner_hypervisors(self):
        testing_hypervisor_id = random_string("testHypervisor")
        self.cp.updateConsumer(self.consumer_uuid, hypervisor_id=testing_hypervisor_id)
        self.cp.getConsumer(self.consumer_uuid)['hypervisorId']

        hypervisors = self.cp.getOwnerHypervisors("admin", [testing_hypervisor_id])

        self.assertEqual(1, len(hypervisors))
        self.assertEqual(self.consumer_uuid, hypervisors[0]['uuid'])

    def tearDown(self):
        self.cp.unregisterConsumer(self.consumer_uuid)


@attr('functional')
class EntitlementRegenerationTests(unittest.TestCase):
    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin", insecure=True)

        self.consumer = self.cp.registerConsumer("test-consumer", "system", owner="admin")
        self.consumer_uuid = self.consumer['uuid']

        # This product is present in the Candlepin test data
        self.cp.bindByProduct(self.consumer_uuid, ["awesomeos-instancebased"])

        entitlements = self.cp.getEntitlementList(self.consumer_uuid)
        self.assertTrue(len(entitlements) > 0)

        self.entitlement = entitlements[0]
        self.entitlement_id = self.entitlement['id']

    def test_regenerate_entitlements_default(self):
        result = self.cp.regenEntitlementCertificates(self.consumer_uuid)
        self.assertTrue(result)

    def test_regenerate_entitlements_lazy(self):
        result = self.cp.regenEntitlementCertificates(self.consumer_uuid, True)
        self.assertTrue(result)

    def test_regenerate_entitlements_eager(self):
        result = self.cp.regenEntitlementCertificates(self.consumer_uuid, False)
        self.assertTrue(result)

    def test_regenerate_entitlements_bad_uuid(self):
        result = self.cp.regenEntitlementCertificates("bad_consumer_uuid")
        self.assertFalse(result)

    def test_regenerate_entitlement_default(self):
        result = self.cp.regenEntitlementCertificate(self.consumer_uuid, self.entitlement_id)
        self.assertTrue(result)

    def test_regenerate_entitlement_lazy(self):
        result = self.cp.regenEntitlementCertificate(self.consumer_uuid, self.entitlement_id, True)
        self.assertTrue(result)

    def test_regenerate_entitlement_eager(self):
        result = self.cp.regenEntitlementCertificate(self.consumer_uuid, self.entitlement_id, False)
        self.assertTrue(result)

    def test_regenerate_entitlement_bad_consumer_uuid(self):
        result = self.cp.regenEntitlementCertificate("bad_consumer_uuid", self.entitlement_id)
        self.assertFalse(result)

    def test_regenerate_entitlement_bad_entitlement_id(self):
        result = self.cp.regenEntitlementCertificate(self.consumer_uuid, "bad_entitlement_id")
        self.assertFalse(result)

    def tearDown(self):
        self.cp.unregisterConsumer(self.consumer_uuid)


@attr('functional')
class BindRequestTests(unittest.TestCase):
    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin", insecure=True)

        consumerInfo = self.cp.registerConsumer("test-consumer", "system", owner="admin")
        self.consumer_uuid = consumerInfo['uuid']

    @patch.object(Restlib, 'validateResponse')
    @patch('rhsm.connection.drift_check', return_value=False)
    @patch('httplib.HTTPSConnection', auto_spec=True)
    def test_bind_no_args(self, mock_conn, mock_drift, mock_validate):

        self.cp.bind(self.consumer_uuid)

        # verify we called request() with kwargs that include 'body' as None
        # Specifically, we are checking that passing in "" to post_request, as
        # it does by default, results in None here. bin() passes no args there
        # so we use the default, "". See  bz #907536
        for (name, args, kwargs) in mock_conn.mock_calls:
            if name == '().request':
                self.assertEqual(None, kwargs['body'])

    @patch.object(Restlib, 'validateResponse')
    @patch('rhsm.connection.drift_check', return_value=False)
    @patch('httplib.HTTPSConnection', auto_spec=True)
    def test_bind_by_pool(self, mock_conn, mock_drift, mock_validate):
        # this test is just to verify we make the httplib connection with
        # right args, we don't validate the bind here
        self.cp.bindByEntitlementPool(self.consumer_uuid, '123121111', '1')
        for (name, args, kwargs) in mock_conn.mock_calls:
            if name == '().request':
                self.assertEqual(None, kwargs['body'])


@attr('functional')
class ContentConnectionTests(unittest.TestCase):

    def testInsecure(self):
        ContentConnection(host="127.0.0.1", insecure=True)

    # sigh camelCase
    def testEnvProxyUrl(self):
        with patch.dict('os.environ', {'https_proxy': 'https://user:pass@example.com:1111'}):
            cc = ContentConnection(host="127.0.0.1")
            self.assertEqual("user", cc.proxy_user)
            self.assertEqual("pass", cc.proxy_password)
            self.assertEqual("example.com", cc.proxy_hostname)
            self.assertEqual(1111, cc.proxy_port)
        assert 'https_proxy' not in os.environ

    def testEnvProxyUrlNoPort(self):
        with patch.dict('os.environ', {'https_proxy': 'https://user:pass@example.com'}):
            cc = ContentConnection(host="127.0.0.1")
            self.assertEqual("user", cc.proxy_user)
            self.assertEqual("pass", cc.proxy_password)
            self.assertEqual("example.com", cc.proxy_hostname)
            self.assertEqual(3128, cc.proxy_port)
        assert 'https_proxy' not in os.environ

    def testEnvProxyUrlNouserOrPass(self):
        with patch.dict('os.environ', {'https_proxy': 'https://example.com'}):
            cc = ContentConnection(host="127.0.0.1")
            self.assertEqual(None, cc.proxy_user)
            self.assertEqual(None, cc.proxy_password)
            self.assertEqual("example.com", cc.proxy_hostname)
            self.assertEqual(3128, cc.proxy_port)
        assert 'https_proxy' not in os.environ

    def testEnvNoProxy(self):
        with patch.dict('os.environ', {'no_proxy': '.localdomain',
                                       'https_proxy': 'https://example.com'}):
            cc = ContentConnection(host="localhost.localdomain")
            self.assertEquals(None, cc.proxy_user)
            self.assertEquals(None, cc.proxy_password)
            self.assertEquals(None, cc.proxy_hostname)
            self.assertEquals(None, cc.proxy_port)
        assert 'no_proxy' not in os.environ and 'https_proxy' not in os.environ

    def testEnvNoProxyWithAsterisk(self):
        with patch.dict('os.environ', {'no_proxy': '*.localdomain',
                                       'https_proxy': 'https://example.com'}):
            cc = ContentConnection(host="localhost.localdomain")
            self.assertEquals(None, cc.proxy_user)
            self.assertEquals(None, cc.proxy_password)
            self.assertEquals(None, cc.proxy_hostname)
            self.assertEquals(None, cc.proxy_port)
        assert 'no_proxy' not in os.environ and 'https_proxy' not in os.environ


@attr('functional')
class HypervisorCheckinTests(unittest.TestCase):

    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin",
                insecure=True)

    def test_hypervisor_checkin_can_pass_empty_map_and_updates_nothing(self):
        response = self.cp.hypervisorCheckIn("admin", "", {})
        if self.cp.has_capability('hypervisors_async'):
            self.assertEqual(response['resultData'], None)
        else:
            self.assertEqual(len(response['failedUpdate']), 0)
            self.assertEqual(len(response['updated']), 0)
            self.assertEqual(len(response['created']), 0)


@attr('functional')
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

    def test_standard_error_handling_on_401_with_invalid_json_body(self):
        self._run_standard_error_handling_test_invalid_json(401, UnauthorizedException)

    def test_invalid_credentitals_thrown_on_403_with_empty_body(self):
        mock_response = {"status": 403}
        self.assertRaises(ForbiddenException, self._validate_response,
                          mock_response)

    def test_standard_error_handling_on_403_with_defined_body(self):
        self._run_standard_error_handling_test(403)

    def test_standard_error_handling_on_403_with_invalid_json_body(self):
        self._run_standard_error_handling_test_invalid_json(403, ForbiddenException)

    def _run_standard_error_handling_test_invalid_json(self, expected_error_code,
                                                       expected_exception):
        mock_response = {"status": expected_error_code,
                         "content": '<this is not valid json>>'}

        self._check_for_remote_server_exception(expected_error_code,
                                                expected_exception,
                                                mock_response)

    def _run_standard_error_handling_test(self, expected_error):
        expected_error = "My Expected Error."
        mock_response = {"status": expected_error,
                         "content": '{"displayMessage":"%s"}' % expected_error}

        try:
            self._validate_response(mock_response)
            self.fail("An exception should have been thrown.")
        except Exception as ex:
            self.assertTrue(isinstance(ex, RestlibException))
            self.assertEqual(expected_error, ex.code)
            self.assertEqual(expected_error, str(ex))

    def _check_for_remote_server_exception(self, expected_error_code,
                                           expected_exception, mock_response):
        try:
            self._validate_response(mock_response)
            self.fail("An %s exception should have been thrown." % expected_exception)
        except Exception as ex:
            self.assertTrue(isinstance(ex, expected_exception))
            self.assertEqual(expected_error_code, ex.code)


@attr('functional')
class OwnerInfoTests(unittest.TestCase):
    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin",
                                insecure=True)
        self.owner_key = "test_owner_%d" % (random.randint(1, 5000))
        self.cp.conn.request_post('/owners', {'key': self.owner_key,
                                              'displayName': self.owner_key})

    def test_get_owner_info(self):
        owner_info = self.cp.getOwnerInfo(self.owner_key)
        self.assertTrue(owner_info is not None)
