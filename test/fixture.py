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

# WARNING: Important that this runs early to make sure the config is 
# overwritten before things start happening:
import os
import config
test_config = os.path.abspath(os.path.join(os.path.dirname(__file__),
    'rhsmtest.conf'))
cfg = config.initConfig(config_file=test_config)

import unittest
import shutil


class RhsmFunctionalTest(unittest.TestCase):

    def setUp(self):
        self.test_dir = cfg.get('test', 'tmpDir')
        if not os.path.exists(self.test_dir):
            os.mkdir(self.test_dir)
            os.makedirs(os.path.join(self.test_dir, 'etc', 'pki', 'consumer'))

    def tearDown(self):
        shutil.rmtree(self.test_dir)



