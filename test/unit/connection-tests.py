# -*- coding: utf-8 -*-
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

from rhsm.connection import UEPConnection, Restlib, ConnectionException, ConnectionSetupException, \
        BadCertificateException, RestlibException, GoneException, NetworkException, \
        RemoteServerException, drift_check, ExpiredIdentityCertException, UnauthorizedException, \
        ForbiddenException, AuthenticationException, RateLimitExceededException

from mock import Mock, patch
from datetime import date
from time import strftime, gmtime
from rhsm import ourjson as json


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        # NOTE: this won't actually work, idea for this suite of unit tests
        # is to mock the actual server responses and just test logic in the
        # UEPConnection:
        self.cp = UEPConnection(username="dummy", password="dummy",
                handler="/Test/", insecure=True)

    def test_accepts_a_timeout(self):
        self.cp = UEPConnection(username="dummy", password="dummy",
                handler="/Test/", insecure=True, timeout=3)

    def test_load_manager_capabilities(self):
        expected_capabilities = ['hypervisors_async', 'cores']
        proper_status = {'version': '1',
                         'result': True,
                         'managerCapabilities': expected_capabilities}
        improper_status = dict.copy(proper_status)
        # Remove the managerCapabilities key from the dict
        del improper_status['managerCapabilities']
        self.cp.conn = Mock()
        # The first call will return the proper_status, the second, the improper
        # status
        original_getStatus = self.cp.getStatus
        self.cp.getStatus = Mock(side_effect=[proper_status,
                                                     improper_status])
        actual_capabilities = self.cp._load_manager_capabilities()
        self.assertEquals(sorted(actual_capabilities),
                          sorted(expected_capabilities))
        self.assertEquals([], self.cp._load_manager_capabilities())
        self.cp.getStatus = original_getStatus

    def test_get_environment_by_name_requires_owner(self):
        self.assertRaises(Exception, self.cp.getEnvironment, None, {"name": "env name"})

    def test_get_environment_urlencoding(self):
        self.cp.conn = Mock()
        self.cp.conn.request_get = Mock(return_value=[])
        self.cp.getEnvironment(owner_key="myorg", name="env name__++=*&")
        self.cp.conn.request_get.assert_called_with(
                "/owners/myorg/environments?name=env+name__%2B%2B%3D%2A%26")

    def test_entitle_date(self):
        self.cp.conn = Mock()
        self.cp.conn.request_post = Mock(return_value=[])
        self.cp.bind("abcd", date(2011, 9, 2))
        self.cp.conn.request_post.assert_called_with(
                "/consumers/abcd/entitlements?entitle_date=2011-09-02")

    def test_no_entitle_date(self):
        self.cp.conn = Mock()
        self.cp.conn.request_post = Mock(return_value=[])
        self.cp.bind("abcd")
        self.cp.conn.request_post.assert_called_with("/consumers/abcd/entitlements")

    def test_clean_up_prefix(self):
        self.assertTrue(self.cp.handler == "/Test")

    def test_https_proxy_info_allcaps(self):
        with patch.dict('os.environ', {'HTTPS_PROXY': 'http://u:p@host:4444'}):
            uep = UEPConnection(username="dummy", password="dummy",
                 handler="/Test/", insecure=True)
            self.assertEquals("u", uep.proxy_user)
            self.assertEquals("p", uep.proxy_password)
            self.assertEquals("host", uep.proxy_hostname)
            self.assertEquals(int("4444"), uep.proxy_port)

    def test_order(self):
        # should follow the order: HTTPS, https, HTTP, http
        with patch.dict('os.environ', {'HTTPS_PROXY': 'http://u:p@host:4444', 'http_proxy': 'http://notme:orme@host:2222'}):
            uep = UEPConnection(username="dummy", password="dummy",
                 handler="/Test/", insecure=True)
            self.assertEquals("u", uep.proxy_user)
            self.assertEquals("p", uep.proxy_password)
            self.assertEquals("host", uep.proxy_hostname)
            self.assertEquals(int("4444"), uep.proxy_port)

    def test_no_port(self):
        with patch.dict('os.environ', {'HTTPS_PROXY': 'http://u:p@host'}):
            uep = UEPConnection(username="dummy", password="dummy",
                 handler="/Test/", insecure=True)
            self.assertEquals("u", uep.proxy_user)
            self.assertEquals("p", uep.proxy_password)
            self.assertEquals("host", uep.proxy_hostname)
            self.assertEquals(3128, uep.proxy_port)

    def test_no_user_or_password(self):
        with patch.dict('os.environ', {'HTTPS_PROXY': 'http://host:1111'}):
            uep = UEPConnection(username="dummy", password="dummy",
                 handler="/Test/", insecure=True)
            self.assertEquals(None, uep.proxy_user)
            self.assertEquals(None, uep.proxy_password)
            self.assertEquals("host", uep.proxy_hostname)
            self.assertEquals(int("1111"), uep.proxy_port)

    def test_sanitizeGuestIds_supports_strs(self):
        self.cp.supports_resource = Mock(return_value=True)
        guestIds = ['test' + str(i) for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # When strings are given, they should always be unchanged
        self.assertEquals(guestIds, resultGuestIds)

    def test_sanitizeGuestIds_no_support_strs(self):
        self.cp.supports_resource = Mock(return_value=False)
        guestIds = ['test' + str(i) for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # When strings are given, they should always be unchanged
        self.assertEquals(guestIds, resultGuestIds)

    def test_sanitizeGuestIds_supports_data(self):
        self.cp.supports_resource = Mock(return_value=True)
        guestIds = [{'guestId': 'test' + str(i)} for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # The dictionary should be unchanged because the server supports guestIds
        self.assertEquals(guestIds, resultGuestIds)

    def test_sanitizeGuestIds_doesnt_support_data(self):
        self.cp.supports_resource = Mock(return_value=False)
        guestIds = [{'guestId': 'test' + str(i)} for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # The result list should only be string ids because the server
        # doesn't support additional data
        expected_guestIds = [guestId['guestId'] for guestId in guestIds]
        self.assertEquals(expected_guestIds, resultGuestIds)


class RestlibValidateResponseTests(unittest.TestCase):
    def setUp(self):
        self.restlib = Restlib("somehost", "123", "somehandler")
        self.request_type = "GET"
        self.handler = "https://server/path"

    def vr(self, status, content, headers=None):
        response = {'status': status,
                    'content': content}
        if headers:
            response['headers'] = headers
        self.restlib.validateResponse(response, self.request_type, self.handler)

    # All empty responses that aren't 200/204 raise a NetworkException
    def test_200_empty(self):
        # this should just not raise any exceptions
        self.vr("200", "")

    def test_200_json(self):
        # no exceptions
        content = u'{"something": "whatever"}'
        self.vr("200", content)

    # 202 ACCEPTED
    def test_202_empty(self):
        self.vr("202", "")

    def test_202_none(self):
        self.vr("202", None)

    def test_202_json(self):
        content = u'{"something": "whatever"}'
        self.vr("202", content)

    # 204 NO CONTENT
    # no exceptions is okay
    def test_204_empty(self):
        self.vr("204", "")

    # no exceptions is okay
    def test_204_none(self):
        self.vr("204", None)

    # MOVED PERMANENTLY
    # FIXME: implement 301 support?
    # def test_301_empty(self):
    #     self.vr("301", "")

    def test_400_empty(self):
        # FIXME: not sure 400 makes sense as "NetworkException"
        #        we check for NetworkException in several places in
        #        addition to RestlibException and RemoteServerException
        #        I think maybe a 400 ("Bad Request") should be a
        #        RemoteServerException
        self.assertRaises(NetworkException,
                          self.vr,
                          "400",
                          "")

    def test_401_empty(self):
        try:
            self.vr("401", "")
        except UnauthorizedException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals("401", e.code)
            expected_str = "Server error attempting a GET to https://server/path returned status 401\n" \
                       "Unauthorized: Invalid credentials for request."
            self.assertEquals(expected_str, str(e))
        else:
            self.fail("Should have raised UnauthorizedException")

    def test_401_invalid_json(self):
        content = u'{this is not json</> dfsdf"" '
        try:
            self.vr("401", content)
        except UnauthorizedException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals("401", e.code)
            expected_str = "Server error attempting a GET to https://server/path returned status 401\n" \
                       "Unauthorized: Invalid credentials for request."
            self.assertEquals(expected_str, str(e))
        else:
            self.fail("Should have raised UnauthorizedException")

    @patch("rhsm.connection.json.loads")
    def test_401_json_exception(self, mock_json_loads):
        mock_json_loads.side_effect = Exception
        content = u'{"errors": ["Forbidden message"]}'
        try:
            self.vr("401", content)
        except UnauthorizedException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals("401", e.code)
            expected_str = "Server error attempting a GET to https://server/path returned status 401\n" \
                       "Unauthorized: Invalid credentials for request."
            self.assertEquals(expected_str, str(e))
        else:
            self.fail("Should have raised UnauthorizedException")

    def test_403_valid(self):
        content = u'{"errors": ["Forbidden message"]}'
        try:
            self.vr("403", content)
        except RestlibException as e:
            self.assertEquals("403", e.code)
            self.assertEquals("Forbidden message", e.msg)
        else:
            self.fails("Should have raised a RestlibException")

    def test_403_empty(self):
        try:
            self.vr("403", "")
        except ForbiddenException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals("403", e.code)
            expected_str = "Server error attempting a GET to https://server/path returned status 403\n" \
                       "Forbidden: Invalid credentials for request."
            self.assertEquals(expected_str, str(e))
        else:
            self.fail("Should have raised ForbiddenException")

    def test_401_valid(self):
        content = u'{"errors": ["Unauthorized message"]}'
        try:
            self.vr("401", content)
        except RestlibException as e:
            self.assertEquals("401", e.code)
            self.assertEquals("Unauthorized message", e.msg)
        else:
            self.fails("Should have raised a RestlibException")

    def test_404_empty(self):
        try:
            self.vr("404", "")
        except RemoteServerException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals(self.handler, e.handler)
            self.assertEquals("404", e.code)
            self.assertEquals("Server error attempting a GET to https://server/path returned status 404", str(e))
        else:
            self.fails("Should have raise RemoteServerException")

    def test_404_valid_but_irrelevant_json(self):
        content = u'{"something": "whatever"}'
        try:
            self.vr("404", content)
        except RestlibException as e:
            self.assertEquals("404", e.code)
            self.assertEquals("", e.msg)
        else:
            self.fails("Should have raised a RemoteServerException")

    def test_404_valid_body_old_style(self):
        content = u'{"displayMessage": "not found"}'
        try:
            self.vr("404", content)
        except RestlibException as e:
            self.assertEquals("not found", e.msg)
            self.assertEquals("404", e.code)
        except Exception as e:
            self.fail("RestlibException expected, got %s" % e)
        else:
            self.fail("RestlibException expected")

    def test_404_valid_body(self):
        content = u'{"errors": ["not found", "still not found"]}'
        try:
            self.vr("404", content)
        except RestlibException as e:
            self.assertEquals("not found still not found", e.msg)
            self.assertEquals("404", e.code)
        except Exception as e:
            self.fail("RestlibException expected, got %s" % e)
        else:
            self.fail("RestlibException expected")

    def test_410_emtpy(self):
        try:
            self.vr("410", "")
        except RemoteServerException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals(self.handler, e.handler)
        else:
            self.fail("RemoteServerException expected")

    def test_410_body(self):
        content = u'{"displayMessage": "foo", "deletedId": "12345"}'
        # self.assertRaises(GoneException, self.vr, "410", content)
        try:
            self.vr("410", content)
        except GoneException as e:
            self.assertEquals("12345", e.deleted_id)
            self.assertEquals("foo", e.msg)
            self.assertEquals("410", e.code)
        else:
            self.fail("Should have raised a GoneException")

    def test_429_empty(self):
        try:
            self.vr("429", "")
        except RateLimitExceededException as e:
            self.assertEquals("429", e.code)
        else:
            self.fail("Should have raised a RateLimitExceededException")

    def test_429_body(self):
        content = u'{"errors": ["TooFast"]}'
        headers = {'Retry-After': 20}
        try:
            self.vr("429", content, headers)
        except RateLimitExceededException as e:
            self.assertEquals(20, e.retry_after)
            self.assertEquals("TooFast", e.msg)
            self.assertEquals("429", e.code)
        else:
            self.fail("Should have raised a RateLimitExceededException")

    def test_500_empty(self):
        try:
            self.vr("500", "")
        except RemoteServerException as e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals(self.handler, e.handler)
        else:
            self.fail("RemoteServerException expected")

    def test_599_emtpty(self):
        self.assertRaises(NetworkException, self.vr, "599", "")


class RestlibTests(unittest.TestCase):

    def test_json_uft8_encoding(self):
        # A unicode string containing JSON
        test_json = u"""
            {
                "firstName": "John",
                "message": "こんにちは世界",
                "address": { "street": "21 2nd Street" },
                "phoneNumbers": [
                    [
                        { "type": "home", "number": "212 555-1234" },
                        { "type": "fax", "number": "646 555-4567" }
                    ]
                ]
            }
        """
        restlib = Restlib("somehost", "123", "somehandler")
        data = json.loads(test_json, object_hook=restlib._decode_dict)
        self.assertTrue(isinstance(data["message"], str))
        # Access a value deep in the structure to make sure we recursed down.
        self.assertTrue(isinstance(data["phoneNumbers"][0][0]["type"], str))


# see #830767 and #842885 for examples of why this is
# a useful test. Aka, sometimes we forget to make
# str/repr work and that cases weirdness
class ExceptionTest(unittest.TestCase):
    exception = Exception
    parent_exception = Exception

    def _stringify(self, e):
        # FIXME: validate results are strings, unicode, etc
        # but just looking for exceptions atm
        # - no assertIsInstance on 2.4/2.6
        self.assertTrue(isinstance("%s" % e, basestring))
        self.assertTrue(isinstance("%s" % str(e), basestring))
        self.assertTrue(isinstance("%s" % repr(e), basestring))

    def _create_exception(self, *args, **kwargs):
        return self.exception(args, kwargs)

    def _test(self):
        e = self._create_exception()
        self._stringify(e)

    def test_exception_str(self):
        self._test()

    def _raise(self):
        raise self._create_exception()

    def test_catch_exception(self):
        self.assertRaises(Exception, self._raise)

    def test_catch_parent(self):
        self.assertRaises(self.parent_exception, self._raise)


# not all our exceptions take a msg arg
class ExceptionMsgTest(ExceptionTest):
    def test_exception_str_with_msg(self):
        e = self._create_exception("I have a bad feeling about this")
        self._stringify(e)


class ConnectionExceptionText(ExceptionMsgTest):
    exception = ConnectionException


class ConnectionSetupExceptionTest(ExceptionMsgTest):
    exception = ConnectionSetupException
    parent_exception = ConnectionException


class BadCertificateExceptionTest(ExceptionTest):
    exception = BadCertificateException
    parent_exception = ConnectionException

    def _create_exception(self, *args, **kwargs):
        kwargs['cert_path'] = "/etc/sdfsd"
        return self.exception(*args, **kwargs)


class RestlibExceptionTest(ExceptionTest):
    exception = RestlibException
    parent_exception = ConnectionException

    def _create_exception(self, *args, **kwargs):
        kwargs['msg'] = "foo"
        kwargs['code'] = 404
        return self.exception(*args, **kwargs)


class RemoteServerExceptionTest(ExceptionTest):
    exception = RemoteServerException
    parent_exception = ConnectionException
    code = 500
    request_type = "GET"
    handler = "htttps://server/path"

    def _create_exception(self, *args, **kwargs):
        kwargs['code'] = self.code
        kwargs['request_type'] = self.request_type
        kwargs['handler'] = self.handler
        return self.exception(*args, **kwargs)


class AuthenticationExceptionTest(RemoteServerExceptionTest):
    exception = AuthenticationException
    parent_exception = RemoteServerException
    code = 401


class UnauthorizedExceptionTest(RemoteServerExceptionTest):
    exception = UnauthorizedException
    parent_exception = AuthenticationException
    code = 401


class ForbiddenExceptionTest(RemoteServerExceptionTest):
    exception = ForbiddenException
    parent_exception = AuthenticationException
    code = 403


class DriftTest(unittest.TestCase):

    def test_big_drift(self):
        # let's move this back to just a few hours before the
        # end of time, so this test doesn't fail on 32bit machines
        self.assertTrue(drift_check("Mon, 18 Jan 2038 19:10:56 GMT", 6))

    def test_no_drift(self):
        header = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())
        self.assertFalse(drift_check(header))


class GoneExceptionTest(ExceptionTest):
    exception = GoneException
    parent_exception = RestlibException

    def setUp(self):
        self.code = 410
        self.deleted_id = 12345

    def _create_exception(self, *args, **kwargs):
        kwargs['msg'] = "foo is gone"
        kwargs['code'] = self.code
        kwargs['deleted_id'] = self.deleted_id
        return self.exception(*args, **kwargs)

    # hmm, maybe these should fail?
    def test_non_int_code(self):
        self.code = "410"
        self._test()

    def test_even_less_int_code(self):
        self.code = "asdfzczcvzcv"
        self._test()


class ExpiredIdentityCertTest(ExceptionTest):
    exception = ExpiredIdentityCertException
    parent_exception = ConnectionException

    def _create_exception(self, *args, **kwargs):
        return self.exception(*args, **kwargs)
