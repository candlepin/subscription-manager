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

import unittest
from certlib import *

class PathTests(unittest.TestCase):

    def test_normal_root(self):
        # this is the default, but have to set it as other tests can modify
        # it if they run first.
        Path.ROOT = '/'
        self.assertEquals('/etc/pki/consumer/', Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/etc/pki/consumer/', Path.abs('etc/pki/consumer/'))

    def test_modified_root(self):
        Path.ROOT = '/mnt/sysimage/'
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_modified_root_no_trailing_slash(self):
        Path.ROOT = '/mnt/sysimage'
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))
