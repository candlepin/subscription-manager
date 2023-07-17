# Copyright (c) 2016 Red Hat, Inc.
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

import rhsmlib.facts.all
from rhsmlib.dbus.facts.base import FactsImplementation

from test.rhsmlib.base import SubManDBusFixture


class TestFactsDBusObject(SubManDBusFixture):
    def setUp(self) -> None:
        super().setUp()
        self.impl = FactsImplementation(collector_class=rhsmlib.facts.all.AllFactsCollector)

    def test_GetFacts(self):
        expected = "uname.machine"
        result = self.impl.get_facts()
        self.assertIn(expected, result)
