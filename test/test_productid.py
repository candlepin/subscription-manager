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
from productid import *
from certlib import Path
import os.path

class ProductDatabaseTests(unittest.TestCase):

    # Testing an error that surfaced during anaconda:
    def test_path(self):
        # Fake that the product database exists to avoid permissions problems:
        def dummy_exists(filename):
            return True
        os.path.exists = dummy_exists

        Path.ROOT = '/mnt/sysimage'
        prod_db = ProductDatabase()
        self.assertEquals('/mnt/sysimage/var/lib/rhsm/productid.js',
                prod_db.dir.abspath('productid.js'))
