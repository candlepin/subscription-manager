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

import os
import config
# WARNING: Important that this runs early to make sure the config is 
# overwritten before things start happening:
test_config = os.path.abspath(os.path.join(os.path.dirname(__file__),
    'rhsmtest.conf'))
cfg = config.initConfig(config_file=test_config)

import connection
from managercli import RegisterCommand

import unittest
import shutil

# WARNING: will be cleaned up in teardown:
TEST_DIR = cfg.get('test', 'tmpDir')


class RhsmFunctionalTest(unittest.TestCase):

    def setUp(self):
        if not os.path.exists(TEST_DIR):
            os.mkdir(TEST_DIR)
            os.makedirs(os.path.join(TEST_DIR, 'etc', 'pki', 'consumer'))

    def tearDown(self):
        shutil.rmtree(TEST_DIR)


class RegistrationTests(RhsmFunctionalTest):

    def test_something(self):
        cmd = RegisterCommand()
        cmd.main(['register', '--username=testuser1', '--password=password'])
        self.assertTrue(os.path.exists(os.path.join(TEST_DIR, 'etc', 'pki', 
            'consumer', 'cert.pem')))
        self.assertTrue(os.path.exists(os.path.join(TEST_DIR, 'etc', 'pki', 
            'consumer', 'key.pem')))

