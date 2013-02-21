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

from rct.manifest_commands import get_value


class RCTManifestCommandTests(unittest.TestCase):

    def test_get_value(self):
        data = {"test": "value", "test2": {"key2": "value2", "key3": []}}
        self.assertEquals("", get_value(data, "some.test"))
        self.assertEquals("", get_value(data, ""))
        self.assertEquals("", get_value(data, "test2.key4"))
        self.assertEquals("", get_value(data, "test2.key2.fred"))
        self.assertEquals("value", get_value(data, "test"))
        self.assertEquals("value2", get_value(data, "test2.key2"))
        self.assertEquals([], get_value(data, "test2.key3"))
