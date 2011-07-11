#
# Copyright (c) 2011 Red Hat, Inc.
#
# Authors: Devan Goodwin <dgoodwin@redhat.com>
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

from rhsm.connection import *
from mock import Mock

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


