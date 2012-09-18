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


import datetime
import gobject
import unittest

import mock

from subscription_manager import async
from subscription_manager import managerlib

import stubs


# some bits we end up calling from list pools
class ListPoolsStubUEP(stubs.StubUEP):
    def getOwner(self, consumeruuid):
        return {'key': 'owner'}

    def getPoolsList(self, consumer, listAll=None, active_on=None, owner=None):
        return []

    def getEntitlementList(self, consumeruuid=None):
        return []


class TestAsyncPool(unittest.TestCase):
    def setUp(self):
        self.callbacks = []

    def callback(self, data, error):
        self.callbacks.append((data, error))

    def idle_callback(self, *args):
        # hit the refresh a few times, out stubbed
        # refresh doesn't really do anything though
        self.ap.refresh(datetime.date.today(), self.callback)
        self.count = self.count + 1
        if self.count > 3:
            self.mainloop.quit()
        return True

    def _create_async_pool(self):
        consumer_mock = mock.Mock()
        consumer_mock.uuid.return_value = 'some-consumer-uuid'
        facts_mock = mock.Mock()
        facts_mock.update_check.return_value = None

        self.pool_stash = \
            managerlib.PoolStash(backend=stubs.StubBackend(uep=ListPoolsStubUEP()),
                                                           consumer=consumer_mock,
                                                           facts=facts_mock)

        self.ap = async.AsyncPool(self.pool_stash)

        # add a timeout and a idle handler
        self.count = 0
        self.idle = gobject.idle_add(self.ap.refresh, datetime.date.today(), self.idle_callback)
        self.timer = gobject.timeout_add(50, self.idle_callback)
        self.mainloop = gobject.MainLoop()

    def test(self):
        self._create_async_pool()

        self.mainloop.run()
        # verify our callback got called a few times
        self.assertTrue(len(self.callbacks) > 0)

    def test_exception(self):
        self._create_async_pool()

        # simulate a exception on pool refresh
        self.pool_stash.refresh = mock.Mock()
        self.pool_stash.refresh.side_effect = IOError()

        self.mainloop.run()
        self.assertTrue(len(self.callbacks) > 0)
        # we should have an exception in the error from the callback
        self.assertTrue(isinstance(self.callbacks[0][1], IOError))
