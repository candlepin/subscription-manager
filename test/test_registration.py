#
# Copyright (c) 2010 Red Hat, Inc.
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

from fixture import RhsmFunctionalTest

import connection
from managercli import RegisterCommand
import config

import os
import unittest

class CliRegistrationTests(RhsmFunctionalTest):

    def test_registration(self):
        cmd = RegisterCommand()
        cmd.main(['register', '--username=testuser1', '--password=password'])
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'etc', 'pki',
            'consumer', 'cert.pem')))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'etc', 'pki',
            'consumer', 'key.pem')))

