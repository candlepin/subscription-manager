# Copyright (c) 2013 Red Hat, Inc.
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

import mock

import fixture

from subscription_manager import healinglib


class TestHealingLib(fixture.SubManFixture):
    def setUp(self):
        super(TestHealingLib, self).setUp()

    def test_autoheal_off(self):
        mock_uep = mock.Mock()
        mock_uep.getConsumer = mock.Mock(return_value=self._consumer())
        hl = healinglib.HealingLib(uep=mock_uep)
        hl.update()

    def test_autoheal_on(self):
        mock_uep = mock.Mock()
        consumer = {'autoheal': True}
        mock_uep.getConsumer = mock.Mock(return_value=consumer)
        hl = healinglib.HealingLib(uep=mock_uep)
        report = hl.update()
        print report
        report.print_exceptions()

    def _consumer(self):
        consumer = {}
        return consumer


class TestHealingUpdateAction(fixture.SubManFixture):
    # HealingLib is very thin wrapper to HealingUpdateAction atm,
    # so basically the same tests
    def setUp(self):
        super(TestHealingUpdateAction, self).setUp()

    def test_autoheal_off(self):
        mock_uep = mock.Mock()
        # nothing set on consumer
        consumer = {}
        mock_uep.getConsumer = mock.Mock(return_value=consumer)
        hl = healinglib.HealingUpdateAction(uep=mock_uep)
        report = hl.perform()
        print report

    def test_autoheal_on(self):
        mock_uep = mock.Mock()
        consumer = {'autoheal': True}
        mock_uep.getConsumer = mock.Mock(return_value=consumer)
        hl = healinglib.HealingUpdateAction(uep=mock_uep)
        report = hl.perform()
        print report
        report.print_exceptions()

