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

from . import fixture

from subscription_manager import healinglib


class TestHealingActionInvoker(fixture.SubManFixture):
    def setUp(self):
        super(TestHealingActionInvoker, self).setUp()

    def test_autoheal_off(self):
        mock_uep = mock.Mock()
        mock_uep.getConsumer = mock.Mock(return_value=self._consumer())
        self.set_consumer_auth_cp(mock_uep)

        hl = healinglib.HealingActionInvoker()
        hl.update()

    def test_autoheal_on(self):
        mock_uep = mock.Mock()
        consumer = {'autoheal': True}
        mock_uep.getConsumer = mock.Mock(return_value=consumer)
        self.set_consumer_auth_cp(mock_uep)

        hl = healinglib.HealingActionInvoker()
        report = hl.update()
        report.print_exceptions()

    def _consumer(self):
        consumer = {}
        return consumer


# FIXME: assert something
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
        self.set_consumer_auth_cp(mock_uep)

        hl = healinglib.HealingUpdateAction()
        hl.perform()

    def test_autoheal_on(self):
        mock_uep = mock.Mock()
        consumer = {'autoheal': True}
        mock_uep.getConsumer = mock.Mock(return_value=consumer)
        self.set_consumer_auth_cp(mock_uep)

        hl = healinglib.HealingUpdateAction()
        hl.perform()
