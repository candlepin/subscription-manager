#
# Copyright (c) 2011 Red Hat, Inc.
#
# Authors: Chris Duryee <cduryee@redhat.com>
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
from tempfile import NamedTemporaryFile

from rhsm.config import *

TEST_CONFIG = """
[foo]
bar =
[server]
hostname = server.example.conf
prefix = /candlepin
port = 8443
insecure = 1
ssl_verify_depth = 3
ca_cert_dir = /etc/rhsm/ca/
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =

[rhsm]
baseurl= https://content.example.com
repo_ca_cert = %(ca_cert_dir)sredhat-uep.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer

[rhsmcertd]
certFrequency = 240
"""


class ConfigTests(unittest.TestCase):

    def setUp(self):
        # create a temp file for use as a config file. This should get cleaned
        # up magically at the end of the run.
        self.fid = NamedTemporaryFile(mode='w+b', suffix='.tmp')
        self.fid.write(TEST_CONFIG)
        self.fid.seek(0)

        self.cfgParser = RhsmConfigParser(self.fid.name)

    def testRead(self):
        self.assertEquals(self.cfgParser.get('server', 'hostname'), 'server.example.conf')

    def testSetd(self):
        self.cfgParser.set('rhsm', 'baseurl', 'cod')
        self.assertEquals(self.cfgParser.get('rhsm', 'baseurl'), 'cod')
