from __future__ import print_function, division, absolute_import

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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rhsmlib.facts import insights
from mock import patch
import tempfile
import six


INSIGHT_TEST_UUID = "2d05f031-d20c-40c9-9cee-2a1d7e823ab6"


class TestInsightsCollector(unittest.TestCase):

    def setUp(self):
        self.collector = insights.InsightsCollector()
        self.machine_id_fp = tempfile.NamedTemporaryFile()
        if six.PY3:
            self.machine_id_fp.write(bytes(INSIGHT_TEST_UUID, 'UTF-8'))
        else:
            self.machine_id_fp.write(INSIGHT_TEST_UUID)
        self.machine_id_fp.flush()

    def tearDown(self):
        self.machine_id_fp.close()

    @patch('rhsmlib.facts.insights.insights_constants')
    def test_get_machine_id(self, consts):
        consts.machine_id_file = self.machine_id_fp.name
        fact = self.collector.get_all()
        self.assertIn("insights_id", fact)
        self.assertEqual(fact["insights_id"], INSIGHT_TEST_UUID)

    @patch('rhsmlib.facts.insights.insights_constants')
    def test_not_get_machine_id(self, consts):
        consts.machine_id_file = "/not/existing/file/machine_id"
        fact = self.collector.get_all()
        self.assertEqual(fact, {})

    @patch('rhsmlib.facts.insights.insights_constants', spec=['InsightsConstants'])
    def test_old_insights_api(self, consts):
        # Try to mimic old version of insights client without consts.machine_id_file
        self.assertFalse(hasattr(consts, 'machine_id_file'))
        fact = self.collector.get_all()
        self.assertEqual(fact, {})
