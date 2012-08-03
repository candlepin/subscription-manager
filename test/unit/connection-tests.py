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

from rhsm.connection import UEPConnection, ConnectionException, ConnectionSetupException, \
        BadCertificateException, RestlibException, GoneException, NetworkException, \
        RemoteServerException

from mock import Mock
from datetime import date


class ConnectionTests(unittest.TestCase):

    def setUp(self):
        # NOTE: this won't actually work, idea for this suite of unit tests
        # is to mock the actual server responses and just test logic in the
        # UEPConnection:
        self.cp = UEPConnection(username="dummy", password="dummy",
                insecure=True)

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

    def _create_exception(self,*args, **kwargs):
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
