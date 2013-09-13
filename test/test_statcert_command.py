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

import certdata
import fixture

from rct.cert_commands import StatCertCommand
from rhsm.certificate import create_from_pem

from stubs import MockStdout, MockStderr


class StatCertCommandStub(StatCertCommand):

    def __init__(self, cert_pem):
        super(StatCertCommandStub, self).__init__()
        self._pem = cert_pem
        self._cert = create_from_pem(self._pem)

    def _validate_options(self):
        # Disable validation
        pass

    def _create_cert(self):
        return self._cert

    def _get_pem(self, filename):
        return self._pem


class StatCertCommandTests(fixture.SubManFixture):

    def setUp(self):
        super(StatCertCommandTests, self).setUp()
        self.mock_stdout = MockStdout()
        self.mock_stderr = MockStderr()
        sys.stdout = self.mock_stdout
        sys.stderr = self.mock_stderr

    def _restore_stdout(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def tearDown(self):
        super(StatCertCommandTests, self).tearDown()
        self._restore_stdout()

    def test_product_cert_output(self):
        command = StatCertCommandStub(certdata.PRODUCT_CERT_V1_0)
        command.main(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assert_string_equals(certdata.PRODUCT_CERT_V1_0_STAT_OUTPUT, cert_output)

    def test_product_cert_with_os_name_output(self):
        command = StatCertCommandStub(certdata.PRODUCT_CERT_WITH_OS_NAME_V1_0)
        command.main(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assert_string_equals(certdata.PRODUCT_CERT_WITH_OS_NAME_V1_0_STAT_OUTPUT, cert_output)

    def test_entitlement_cert_output_includes_content_sets(self):
        command = StatCertCommandStub(certdata.ENTITLEMENT_CERT_V3_0)
        command.main(['will_use_stub'])

        cert_output = self.mock_stdout.buffer
        self.assert_string_equals(certdata.ENTITLEMENT_CERT_V3_0_STAT_OUTPUT,
                cert_output)
