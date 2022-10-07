from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import errno
import socket
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.certdirectory import DEFAULT_PRODUCT_CERT_DIR
from rhsm.connection import RestlibException, BadCertificateException, ProxyException, UnknownContentException
from rhsm.https import httplib, ssl
from rhsm.certificate2 import CertificateLoadingError


class MyRuntimeErrorBase(RuntimeError):
    def __init__(self, message):
        RuntimeError.__init__(self, message)


class MyRuntimeError(MyRuntimeErrorBase):
    def __init__(self, message):
        MyRuntimeErrorBase.__init__(self, message)


class OldStyleClass:
    def __init__(self):
        pass


class TestExceptionMapper(unittest.TestCase):

    def test_single_mapped_exception(self):
        expected_message = "Single Exception Message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = (expected_message, mapper.format_using_template)

        err = RuntimeError("Testing")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_subclass_mapped_by_base_class(self):
        expected_message = "Single Exception Message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = (expected_message, mapper.format_using_template)

        err = MyRuntimeError("Testing base class")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_subclass_preferred_over_base_class(self):
        expected_message = "Subclass Exception Message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = ("RuntimeError message", mapper.format_using_template)
        mapper.message_map[MyRuntimeErrorBase] = ("MyRuntimeErrorBase message", mapper.format_using_template)
        mapper.message_map[MyRuntimeError] = (expected_message, mapper.format_using_template)

        err = MyRuntimeError("Logged Only")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_can_map_middle_sub_class(self):
        expected_message = "MyRuntimeErrorBase message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = ("RuntimeError message", mapper.format_using_template)
        mapper.message_map[MyRuntimeErrorBase] = (expected_message, mapper.format_using_template)
        mapper.message_map[MyRuntimeError] = ("MyRuntimeError message", mapper.format_using_template)

        err = MyRuntimeErrorBase("Logged Only")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_search_for_base_class_with_gaps(self):
        mapper = ExceptionMapper()
        expected_message = "RuntimeError message"

        mapper.message_map[RuntimeError] = (expected_message, mapper.format_using_template)
        err = MyRuntimeError("Logged Only")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_restlib_exception_uses_custom_message(self):
        expected_message = "Expected MESSAGE"
        mapper = ExceptionMapper()

        err = RestlibException(404, expected_message)
        self.assertEqual(f"{expected_message} (HTTP error code 404: Not Found)", mapper.get_message(err))

    def test_return_str_when_no_mapped_exception(self):
        expected_message = "Expected message"
        mapper = ExceptionMapper()

        err = RuntimeError(expected_message)
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_can_support_old_style_classes(self):
        expected_message = "Old style class"
        mapper = ExceptionMapper()
        mapper.message_map[OldStyleClass] = (expected_message, mapper.format_using_template)

        err = OldStyleClass()
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_bad_certificate_exception(self):
        expected_message = "Expected MESSAGE"
        mapper = ExceptionMapper()

        sslerr = ssl.SSLError(5, expected_message)
        err = BadCertificateException("foo.pem", sslerr)
        self.assertEqual(f"Bad CA certificate: foo.pem: {expected_message}", mapper.get_message(err))

    def test_connectionerror(self):
        expected_message = "Expected MESSAGE"
        expected_errno = errno.ECONNREFUSED
        mapper = ExceptionMapper()

        err = ConnectionRefusedError(expected_errno, expected_message)
        self.assertEqual(
            f"Connection error: {expected_message} (error code {expected_errno})",
            mapper.get_message(err),
        )

    def test_socket_gaierror(self):
        expected_message = "Expected MESSAGE"
        expected_errno = socket.EAI_NONAME
        mapper = ExceptionMapper()

        err = socket.gaierror(expected_errno, expected_message)
        self.assertEqual(
            f"Network error: {expected_message} (error code {expected_errno})",
            mapper.get_message(err),
        )

    def test_proxyexception_with_exception_oserror(self):
        expected_message = "Expected MESSAGE"
        expected_errno = errno.ECONNREFUSED
        expected_hostname = "hostname"
        expected_port = 1234
        mapper = ExceptionMapper()

        oserr = ConnectionRefusedError(expected_errno, expected_message)
        err = ProxyException(expected_hostname, expected_port, oserr)
        self.assertEqual(
            f"Proxy error: unable to connect to {expected_hostname}:{expected_port}: "
            f"{expected_message} (error code {expected_errno})",
            mapper.get_message(err),
        )

    def test_proxyexception_with_exception_non_oserror(self):
        expected_message = "Expected MESSAGE"
        expected_hostname = "hostname"
        expected_port = 1234
        mapper = ExceptionMapper()

        genericerr = Exception(expected_message)
        err = ProxyException(expected_hostname, expected_port, genericerr)
        self.assertEqual(
            f"Proxy error: unable to connect to {expected_hostname}:{expected_port}: {expected_message}",
            mapper.get_message(err),
        )

    def test_proxyexception_without_exception(self):
        expected_hostname = "hostname"
        expected_port = 1234
        mapper = ExceptionMapper()

        err = ProxyException(expected_hostname, expected_port)
        self.assertEqual(
            f"Proxy error: unable to connect to {expected_hostname}:{expected_port}",
            mapper.get_message(err),
        )

    def test_unknowncontentexception_with_content(self):
        expected_http_code = 404
        expected_http_string = httplib.responses[expected_http_code]
        expected_content_type = "text/plain"
        expected_content_original = "\033[92mExpected GREEN MESSAGE\033[0m"
        expected_content_escaped = "<27>[92mExpected GREEN MESSAGE<27>[0m"
        mapper = ExceptionMapper()

        err = UnknownContentException(expected_http_code, expected_content_type, expected_content_original)
        self.assertEqual(
            f"Unknown server reply (HTTP error code {expected_http_code}: "
            f"{expected_http_string}):\n{expected_content_escaped}",
            mapper.get_message(err),
        )

    def test_unknowncontentexception_without_content(self):
        expected_http_code = 404
        expected_http_string = httplib.responses[expected_http_code]
        mapper = ExceptionMapper()

        err = UnknownContentException(expected_http_code)
        self.assertEqual(
            f"Unknown server reply (HTTP error code {expected_http_code}: {expected_http_string})",
            mapper.get_message(err),
        )

    def test_certificateloadingerror_product_certificate(self):
        expected_library = "X509"
        expected_reason = "Expected MESSAGE"
        expected_path = f"{DEFAULT_PRODUCT_CERT_DIR}/foo.pem"
        mapper = ExceptionMapper()

        err = CertificateLoadingError(expected_library, expected_reason, path=expected_path)
        self.assertEqual(
            f"Bad product certificate: {expected_path}: [{expected_library}] {expected_reason}",
            mapper.get_message(err),
        )

    def test_certificateloadingerror_other_certificate(self):
        expected_library = "X509"
        expected_reason = "Expected MESSAGE"
        expected_path = "/tmp/foo.pem"
        mapper = ExceptionMapper()

        err = CertificateLoadingError(expected_library, expected_reason, path=expected_path)
        self.assertEqual(
            f"Bad certificate: {expected_path}: [{expected_library}] {expected_reason}",
            mapper.get_message(err),
        )

    def test_certificateloadingerror_pem_data(self):
        expected_library = "X509"
        expected_reason = "Expected MESSAGE"
        expected_data = "DOESTHISLOOKLIKEACERT?"
        mapper = ExceptionMapper()

        err = CertificateLoadingError(expected_library, expected_reason, pem=expected_data)
        self.assertEqual(
            f"Bad certificate: [{expected_library}] {expected_reason}\n{expected_data}",
            mapper.get_message(err),
        )

    def test_certificateloadingerror_unknown(self):
        expected_library = "X509"
        expected_reason = "Expected MESSAGE"
        mapper = ExceptionMapper()

        err = CertificateLoadingError(expected_library, expected_reason)
        self.assertEqual(
            f"Bad certificate: [{expected_library}] {expected_reason}",
            mapper.get_message(err),
        )
