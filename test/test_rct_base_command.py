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

import unittest

from mock import patch
from rhsm.certificate import CertificateException
from rct.commands import RCTCliCommand
from subscription_manager.cli import InvalidCLIOptionError


class RCTCliCommandTests(unittest.TestCase):

    def test_file_arg_required(self):
        command = RCTCliCommand()
        try:
            command.main([])
            self.fail("Expected InvalidCLIOptionError since no file arg.")
        except InvalidCLIOptionError, e:
            self.assertEqual("You must specify a certificate file.",
                             str(e))

    def test_invalid_file_arg(self):
        command = RCTCliCommand()
        try:
            command.main(["this_file_does_not_exist.crt"])
            self.fail("Expected InvalidCLIOptionError since no file does not exist.")
        except InvalidCLIOptionError, e:
            self.assertEqual("The specified certificate file does not exist.", str(e))

    @patch("os.path.isfile")
    @patch("rhsm.certificate.create_from_file")
    def test_valid_x509_required(self, mock_create, mock_isfile):
        mock_create.side_effect = CertificateException("error!")
        mock_isfile.return_value = True
        command = RCTCliCommand()

        command._do_command = lambda: command._create_cert()
        try:
            command.main(['dummy-file.pem'])
            self.fail("Expected InvalidCLIOptionError since bad x509 file.")
        except InvalidCLIOptionError, e:
            self.assertEqual(
                    "Unable to read certificate file 'dummy-file.pem': error!",
                    str(e))
