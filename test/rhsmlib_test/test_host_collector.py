# Copyright (c) 2017 Red Hat, Inc.
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

import unittest

import mock

from rhsmlib.facts import host_collector


class HostCollectorTest(unittest.TestCase):

    @mock.patch('locale.getdefaultlocale')
    def test_unknown_locale(self, mock_locale):
        collector = host_collector.HostCollector()
        mock_locale.return_value = (None, None)
        facts = collector.get_all()

        self.assertTrue(isinstance(facts, dict))
        self.assertEqual(facts['system.default_locale'], 'Unknown')

    @mock.patch('locale.getdefaultlocale')
    def test_en_us_utf8_locale(self, mock_locale):
        collector = host_collector.HostCollector()
        mock_locale.return_value = ('en_US', 'UTF-8')
        facts = collector.get_all()

        self.assertTrue(isinstance(facts, dict))
        self.assertEqual(facts['system.default_locale'], 'en_US.UTF-8')

    @mock.patch('locale.getdefaultlocale')
    def test_en_us_no_encoding_locale(self, mock_locale):
        collector = host_collector.HostCollector()
        mock_locale.return_value = ('en_US', None)
        facts = collector.get_all()

        self.assertTrue(isinstance(facts, dict))
        self.assertEqual(facts['system.default_locale'], 'en_US')
