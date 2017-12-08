from __future__ import print_function, division, absolute_import

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
import threading

from mock import patch

from . import fixture


from subscription_manager import certlib
#from subscription_manager import injection as inj


class TestLocker(fixture.SubManFixture):
    def test(self):
        l = certlib.Locker()
        # we inject threading.RLock as the lock implementation in
        # the fixture init. RLock() is actually a factory method
        # that returns a _RLock
        self.assertTrue(isinstance(l.lock, type(threading.RLock())))

    def test_run(self):
        def return_four():
            return 4

        l = certlib.Locker()
        res = l.run(return_four)
        self.assertEqual(4, res)


class TestBaseActionInvoker(fixture.SubManFixture):
    def test(self):
        dl = certlib.BaseActionInvoker()
        self.assertTrue(dl.report is None)
        # we use the fixture inject RLock as the default lock
        self.assertTrue(isinstance(dl.locker, certlib.Locker))

    def test_update(self):
        dl = certlib.BaseActionInvoker()
        report = dl.update()
        # default returns None instead of a report
        self.assertTrue(report is None)

    @patch("subscription_manager.certlib.Locker", spec=certlib.Locker)
    def test_update_locker(self, mocker_locker):
        dl = certlib.BaseActionInvoker()
        dl.update()
        mocker_locker_instance = mocker_locker.return_value
        self.assertTrue(mocker_locker_instance.run.called)


class TestActionReport(fixture.SubManFixture):
    def test(self):
        ar = certlib.ActionReport()
        self.assertEqual(None, ar._status)
        self.assertEqual([], ar._exceptions)
        self.assertEqual([], ar._updates)
        self.assertEqual("Report", ar.name)

    def test_format_exceptions(self):
        ar = certlib.ActionReport()
        exc_list = [Exception("foo"),
                    IOError("blip")]

        for exc in exc_list:
            ar._exceptions.append(exc)

        for exc in exc_list:
            self.assertTrue(exc in ar._exceptions)
