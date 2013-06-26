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
        RemoteServerException, drift_check, ExpiredIdentityCertException

from mock import Mock
from datetime import date
from time import strftime, gmtime
import simplejson as json


class ConnectionTests(unittest.TestCase):

    def setUp(self):
        # NOTE: this won't actually work, idea for this suite of unit tests
        # is to mock the actual server responses and just test logic in the
        # UEPConnection:
        self.cp = UEPConnection(username="dummy", password="dummy",
                handler="/Test/", insecure=True)

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


class RestlibValidateResponseTests(unittest.TestCase):
    def setUp(self):
        self.restlib = Restlib("somehost", "123", "somehandler")
        self.request_type = "GET"
        self.handler = "https://server/path"

    def vr(self, status, content):
        response = {'status': status,
                    'content': content}
        #print "response", response
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
        self.assertRaises(NetworkException, self.vr, "202", "")

    def test_202_none(self):
        self.assertRaises(NetworkException, self.vr, "202", None)

    def test_202_json(self):
        content = u'{"something": "whatever"}'
        try:
            self.vr("202", content)
        except RestlibException, e:
            self.assertEquals("202", e.code)
#            self.assertEquals(self.request_type, e.request_type)
#            self.assertEquals(self.handler, e.handler)
            self.assertTrue(e.msg is "")
        else:
            self.fail("Should of raised a Restlib exception")

    # 204 NO CONTENT
    # no exceptions is okay
    def test_204_empty(self):
        self.vr("204", "")

    # no exceptions is okay
    def test_204_None(self):
        self.vr("204", None)

    # MOVED PERMANENTLY
    def test_301_empty(self):
        self.vr("301", "")

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

    def test_404_empty(self):
        try:
            self.vr("404", "")
        except RemoteServerException, e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals(self.handler, e.handler)
            self.assertEquals("404", e.code)
            self.assertEquals("Server error attempting a GET to https://server/path returned status 404", str(e))
        else:
            self.fails("Should of raise RemoteServerException")

    def test_404_valid_but_irrelevant_json(self):
        content = u'{"something": "whatever"}'
        try:
            self.vr("404", content)
        except RestlibException, e:
            self.assertEquals("404", e.code)
            self.assertEquals("", e.msg)
        else:
            self.fails("Should of raised a RemoteServerException")

    def test_404_valid_body_old_style(self):
        content = u'{"displayMessage": "not found"}'
        try:
            self.vr("404", content)
        except RestlibException, e:
            self.assertEquals("not found", e.msg)
            self.assertEquals("404", e.code)
        except Exception, e:
            self.fail("RestlibException expected, got %s" % e)
        else:
            self.fail("RestlibException expected")

    def test_404_valid_body(self):
        content = u'{"errors": ["not found", "still not found"]}'
        try:
            self.vr("404", content)
        except RestlibException, e:
            self.assertEquals("not found still not found", e.msg)
            self.assertEquals("404", e.code)
        except Exception, e:
            self.fail("RestlibException expected, got %s" % e)
        else:
            self.fail("RestlibException expected")

    def test_410_emtpy(self):
        try:
            self.vr("410", "")
        except RemoteServerException, e:
            self.assertEquals(self.request_type, e.request_type)
            self.assertEquals(self.handler, e.handler)
        else:
            self.fail("RemoteServerException expected")

    def test_410_body(self):
        content = u'{"displayMessage": "foo", "deletedId": "12345"}'
        #self.assertRaises(GoneException, self.vr, "410", content)
        try:
            self.vr("410", content)
        except GoneException, e:
            self.assertEquals("12345", e.deleted_id)
            self.assertEquals("foo", e.msg)
            self.assertEquals("410", e.code)
        else:
            self.fail("Should have raised a GoneException")

    def test_500_empty(self):
        try:
            self.vr("500", "")
        except RemoteServerException, e:
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


# not all our exceptions take a msg arg
class ExceptionMsgTest(ExceptionTest):
    def test_exception_str_with_msg(self):
        e = self._create_exception("I have a bad feeling about this")
        self._stringify(e)


class ConnectionExceptionText(ExceptionMsgTest):
    exception = ConnectionException


class ConnectionSetupExceptionTest(ExceptionMsgTest):
    exception = ConnectionSetupException


class BadCertificateException(ExceptionTest):
    exception = BadCertificateException

    def _create_exception(self, *args, **kwargs):
        kwargs['cert_path'] = "/etc/sdfsd"
        return self.exception(*args, **kwargs)


class RestlibExceptionTest(ExceptionTest):
    exception = RestlibException

    def _create_exception(self, *args, **kwargs):
        kwargs['msg'] = "foo"
        kwargs['code'] = 404
        return self.exception(*args, **kwargs)


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

    def _create_exception(self, *args, **kwargs):
        return self.exception(*args, **kwargs)
