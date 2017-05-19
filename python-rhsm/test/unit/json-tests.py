from __future__ import print_function, division, absolute_import

# Copyright (c) 2015 Red Hat, Inc.
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
from rhsm import ourjson as json


class JsonTests(unittest.TestCase):
    def test_custom_set_encoding(self):
        s = set(['a', 'b', 'c', 'c'])
        result = json.dumps(s, default=json.encode)
        # Python prints lists with single quotes, JSON with double quotes
        # so we need to convert to do a string comparison.
        expected = "[%s]" % ", ".join(['"%s"' % x for x in s])
        self.assertEqual(expected, result)
