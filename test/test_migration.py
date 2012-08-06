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
import re


class TestMigration(unittest.TestCase):

    def setUp(self):
        self.double_mapped_channels = (
            "rhel-i386-client-dts-5-beta",
            "rhel-i386-client-dts-5-beta-debuginfo",
            "rhel-i386-server-dts-5-beta",
            "rhel-i386-server-dts-5-beta-debuginfo",
            "rhel-x86_64-client-dts-5-beta",
            "rhel-x86_64-client-dts-5-beta-debuginfo",
            "rhel-x86_64-server-dts-5-beta",
            "rhel-x86_64-server-dts-5-beta-debuginfo",
            )
        self.single_mapped_channels = (
            "rhel-i386-client-dts-5",
            "rhel-i386-client-dts-5-debuginfo",
            "rhel-x86_64-client-dts-5",
            "rhel-x86_64-client-dts-5-debuginfo",
            "rhel-i386-server-dts-5",
            "rhel-i386-server-dts-5-debuginfo",
            "rhel-x86_64-server-dts-5",
            "rhel-x86_64-server-dts-5-debuginfo",
            )

    def test_double_mapping_regex(self):
        regex = "rhel-.*?-(client|server)-dts-(5|6)-beta(-debuginfo)?"
        for channel in self.double_mapped_channels:
            self.assertTrue(re.match(regex, channel))

        for channel in self.single_mapped_channels:
            self.assertFalse(re.match(regex, channel))

    def test_single_mapping_regex(self):
        regex = "rhel-.*?-(client|server)-dts-(5|6)(?!-beta)(-debuginfo)?"
        for channel in self.double_mapped_channels:
            self.assertFalse(re.match(regex, channel))

        for channel in self.single_mapped_channels:
            self.assertTrue(re.match(regex, channel))
