#
# Copyright (c) 2012 Red Hat, Inc.
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
import sys
import unittest
import certdata
from rt.commands import CatCertCommand
from rhsm.certificate import create_from_pem
from rt.cli import InvalidCLIOptionError

from stubs import MockStdout, MockStderr


class CatCertCommandStub(CatCertCommand):
    """
    A testing CatCertCommand that allows bypassing
    the loading of a certificate file.
    """
    def __init__(self, cert_pem):
        CatCertCommand.__init__(self)
        self.cert = create_from_pem(cert_pem)

    def _validate_options(self):
        # Disable validation
        pass

    def _create_cert(self):
        return self.cert


class CatCertCommandTests(unittest.TestCase):

    def setUp(self):
        self.mock_stdout = MockStdout()
        self.mock_stderr = MockStderr()
        sys.stdout = self.mock_stdout
        sys.stderr = self.mock_stderr

    def _restore_stdout(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def tearDown(self):
        self._restore_stdout()

    def test_file_arg_required(self):
        command = CatCertCommand()
        try:
            sys.argv = ['rt']
            command.run()
            self.fail("Expected InvalidCLIOptionError since no file arg.")
        except InvalidCLIOptionError, e:
            self.assertEqual("You must specify a certificate file.",
                             e.message)

    def test_invalid_file_arg(self):
        command = CatCertCommand()
        try:
            command.run(["this_file_does_not_exist.crt"])
            self.fail("Expected InvalidCLIOptionError since no file does not exist.")
        except InvalidCLIOptionError, e:
            self.assertEqual("The specified certificate file does not exist.", e.message)

    def test_omit_content_list(self):
        command = CatCertCommandStub(certdata.ENTITLEMENT_CERT_V1_0)
        command.run(["not_used.pem", "--no-content"])
        cert_output = self.mock_stdout.buffer
        self.assertTrue(cert_output.find("Content:\n") == -1,
                        "Content was not excluded from the output.")

    def test_omit_product_list(self):
        command = CatCertCommandStub(certdata.ENTITLEMENT_CERT_V1_0)
        command.run(["not_used.pem", "--no-products"])
        cert_output = self.mock_stdout.buffer
        self.assertTrue(cert_output.find("Product:\n") == -1,
                        "Products were not excluded from the output.")

    def test_cert_v1_cat(self):
        command = CatCertCommandStub(certdata.ENTITLEMENT_CERT_V1_0)
        command.run(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assertEqual(certdata.ENTITLEMENT_CERT_V1_0_OUTPUT, cert_output)

    def test_cert_v2_cat(self):
        command = CatCertCommandStub(certdata.ENTITLEMENT_CERT_V2_0)
        command.run(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assertEqual(certdata.ENTITLEMENT_CERT_V2_0_OUTPUT, cert_output)

    def test_product_cert_output(self):
        command = CatCertCommandStub(certdata.PRODUCT_CERT_V1_0)
        command.run(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assertEqual(certdata.PRODUCT_CERT_V1_0_OUTPUT, cert_output)

    def test_identity_cert_output(self):
        command = CatCertCommandStub(certdata.IDENTITY_CERT)
        command.run(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assertEqual(certdata.IDENTITY_CERT_OUTPUT, cert_output)
