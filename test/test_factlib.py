#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import unittest
import tempfile

import stubs

from subscription_manager import factlib
from subscription_manager import certlib


class MockActionLock(certlib.ActionLock):
    PATH = tempfile.mkstemp()[1]

    def __init__(self):
        certlib.ActionLock.__init__(self)


#FIXME: need a mocked/stubbed facts.Facts here
class TestFactlib(unittest.TestCase):

    def setUp(self):
        factlib.ConsumerIdentity = stubs.StubConsumerIdentity
        self.fl = factlib.FactLib(lock=MockActionLock())

    def test_factlib_updates(self):
        self.fl.update()
