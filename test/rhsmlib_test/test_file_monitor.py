from __future__ import print_function, division, absolute_import

# Copyright (c) 2018 Red Hat, Inc.
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

from rhsmlib import file_monitor
from six.moves import configparser
from mock import Mock, patch
from test import fixture
from threading import Thread
import subprocess
import tempfile


class TestFilesystemWatcher(fixture.SubManFixture):
    def setUp(self):
        super(TestFilesystemWatcher, self).setUp()
        self.mock_cb1 = Mock(return_value=None)
        self.mock_cb2 = Mock(return_value=None)
        self.testpath1 = self.write_tempfile("").name
        self.testpath2 = self.write_tempfile("").name
        self.testpath3 = self.write_tempfile("").name
        self.dw1 = file_monitor.DirectoryWatch(self.testpath1, [], is_glob=True)
        self.dw2 = file_monitor.DirectoryWatch(self.testpath2, [], is_glob=False)
        self.dw3 = file_monitor.DirectoryWatch(self.testpath2, [self.mock_cb1, self.mock_cb2], is_glob=False)
        self.dir_list = [self.dw1, self.dw2, self.dw3]
        self.fsw1 = file_monitor.FilesystemWatcher(self.dir_list)
        self.fsw2 = file_monitor.InotifyFilesystemWatcher(self.dir_list)

    def tearDown(self):
        super(TestFilesystemWatcher, self).tearDown()

    @patch("rhsmlib.file_monitor.is_inotify_available")
    @patch("rhsmlib.file_monitor.is_inotify_config")
    def test_create_fsw(self, mock_config, mock_avail):
        """
        Tests that create_filesystem_watcher returns the correct object

        create_filesystem_watcher should return an inotify filesystem watcher if
        pyinotify is available and configured, and a polling filesystem watcher otherwise
        :param mock_config: mock of whether pyinotify is configured or not according to is_inotify_config()
        :param mock_avail: mock of whether pyinotify is available or not according to is_inotify_avail()
        :return:
        """
        mock_config.return_value = True
        mock_avail.return_value = True
        fsw = file_monitor.create_filesystem_watcher(self.dir_list)
        self.assertIsInstance(fsw, file_monitor.InotifyFilesystemWatcher)
        mock_config.return_value = False
        mock_avail.return_value = True
        fsw = file_monitor.create_filesystem_watcher(self.dir_list)
        self.assertIsInstance(fsw, file_monitor.FilesystemWatcher)
        mock_config.return_value = True
        mock_avail.return_value = False
        fsw = file_monitor.create_filesystem_watcher(self.dir_list)
        self.assertIsInstance(fsw, file_monitor.FilesystemWatcher)
        mock_config.return_value = False
        mock_avail.return_value = False
        fsw = file_monitor.create_filesystem_watcher(self.dir_list)
        self.assertIsInstance(fsw, file_monitor.FilesystemWatcher)

    @patch("rhsmlib.file_monitor.pyinotify", new=None)
    def test_inotify_None(self):
        self.assertFalse(file_monitor.is_inotify_available())

    def test_inotify_avail(self):
        self.assertTrue(file_monitor.is_inotify_available(), "expected: inotify is available")

    @patch("rhsmlib.file_monitor.conf")
    def test_inotify_config(self, mock_config):
        """
        test each case of is_inotify_config()

        :param mock_config: mock_config.__getitem__.return_value.get_int.return_value mocks out
        the value of use_notify in is_inotify_config()
        :return:
        """
        mock_config.__getitem__.return_value.get_int.return_value = True
        self.assertTrue(file_monitor.is_inotify_config())
        mock_config.__getitem__.return_value.get_int.side_effect = ValueError("bees?")
        self.assertTrue(file_monitor.is_inotify_config())
        mock_config.__getitem__.return_value.get_int.side_effect = configparser.Error
        self.assertTrue(file_monitor.is_inotify_config())
        mock_config.__getitem__.return_value.get_int.return_value = None
        self.assertTrue(file_monitor.is_inotify_config())

    def test_polling_stop_value_change(self):
        self.assertFalse(self.fsw1.should_stop)
        self.fsw1.stop()
        self.assertTrue(self.fsw1.should_stop)

    def test_polling_changed_dw_set_2_modified(self):
        self.fsw1.changed_dw_set()
        subprocess.call("touch %s -m" % self.testpath1, shell=True)
        subprocess.call("touch %s -m" % self.testpath2, shell=True)
        self.assertEqual(self.fsw1.changed_dw_set(), {self.dw1, self.dw2, self.dw3})

    def test_polling_changed_dw_set_first_modified(self):
        self.fsw1.changed_dw_set()
        subprocess.call("touch %s -m" % self.testpath1, shell=True)
        self.assertEqual(self.fsw1.changed_dw_set(), {self.dw1})

    def test_polling_changed_dw_set_second_modified(self):
        self.fsw1.changed_dw_set()
        subprocess.call("touch %s -m" % self.testpath2, shell=True)
        self.assertEqual(self.fsw1.changed_dw_set(), {self.dw2, self.dw3})

    def test_polling_changed_dw_set_0_modified(self):
        self.fsw1.changed_dw_set()
        self.assertEqual(self.fsw1.changed_dw_set(), set())

    def test_polling_update_2_modified(self):
        self.fsw1.changed_dw_set()
        subprocess.call("touch %s -m" % self.testpath1, shell=True)
        subprocess.call("touch %s -m" % self.testpath2, shell=True)
        self.assertEqual(self.fsw1.update(), {self.dw1, self.dw2, self.dw3})

    def test_polling_update_first_modified(self):
        self.fsw1.changed_dw_set()
        subprocess.call("touch %s -m" % self.testpath1, shell=True)
        self.assertEqual(self.fsw1.update(), {self.dw1})

    def test_polling_update_second_modified(self):
        self.fsw1.changed_dw_set()
        subprocess.call("touch %s -m" % self.testpath2, shell=True)
        self.assertEqual(self.fsw1.update(), {self.dw2, self.dw3})

    def test_polling_update_0_modified(self):
        self.fsw1.changed_dw_set()
        self.assertEqual(self.fsw1.update(), set())

    def test_polling_no_loop_when_stopped(self):
        self.fsw1.should_stop = True
        self.fsw1.loop()

    def test_polling_loop_stops(self):
        test_loop = TestLoop(self.fsw1)
        loop_thread = Thread(target=test_loop.run)
        loop_thread.start()
        self.assertFalse(test_loop.stopped)
        test_loop.fsw.stop()
        loop_thread.join(5.0)
        self.assertTrue(test_loop.stopped)

    def test_inotify_stop_value_change(self):
        self.assertFalse(self.fsw2.should_stop)
        self.fsw2.stop()
        self.assertTrue(self.fsw2.should_stop)

    def test_inotify_no_loop_when_stopped(self):
        self.fsw2.should_stop = True
        self.fsw2.loop()

    @patch("rhsmlib.file_monitor.DirectoryWatch.notify")
    @patch("pyinotify.Event")
    def test_handle_event(self, mock_event, mock_notify):
        mock_event.path = self.testpath1
        mock_event.pathname = self.testpath1
        mock_event.mask = self.dw3.IN_MODIFY
        self.fsw2.handle_event(mock_event)
        self.assertEqual(mock_notify.call_count, 1)
        mock_notify.call_count = 0
        mock_event.mask = 0
        self.fsw2.handle_event(mock_event)
        self.assertEqual(mock_notify.call_count, 0)
        mock_notify.call_count = 0

        mock_event.path = self.testpath2
        mock_event.pathname = self.testpath2
        mock_event.mask = self.dw3.IN_MODIFY
        self.fsw2.handle_event(mock_event)
        self.assertEqual(mock_notify.call_count, 2)
        mock_notify.call_count = 0
        mock_event.mask = 0
        self.fsw2.handle_event(mock_event)
        self.assertEqual(mock_notify.call_count, 0)
        mock_notify.call_count = 0

        mock_event.path = self.testpath3
        mock_event.pathname = self.testpath3
        mock_event.mask = self.dw3.IN_MODIFY
        self.fsw2.handle_event(mock_event)
        self.assertEqual(mock_notify.call_count, 0)
        mock_notify.call_count = 0
        mock_event.mask = 0
        self.fsw2.handle_event(mock_event)
        self.assertEqual(mock_notify.call_count, 0)


class TestDirectoryWatch(fixture.SubManFixture):
    def setUp(self):
        super(TestDirectoryWatch, self).setUp()
        self.mock_cb1 = Mock(return_value=None)
        self.mock_cb2 = Mock(return_value=None)
        self.tmp_file1 = tempfile.NamedTemporaryFile(prefix="directory_watcher_test_")
        self.tmp_file2 = tempfile.NamedTemporaryFile(prefix="directory_watcher_test_")
        self.testpath1 = self.tmp_file1.name
        self.testpath2 = self.tmp_file2.name
        subprocess.call("touch %s" % self.testpath1, shell=True)
        subprocess.call("touch %s" % self.testpath2, shell=True)
        self.dw1 = file_monitor.DirectoryWatch(self.testpath1, [], is_glob=True)
        self.dw2 = file_monitor.DirectoryWatch(self.testpath2, [], is_glob=False)
        self.dw3 = file_monitor.DirectoryWatch(self.testpath2, [self.mock_cb1, self.mock_cb2], is_glob=False)

    def tearDown(self):
        self.tmp_file1.close()
        self.tmp_file2.close()

    def test_notify(self):
        self.dw3.notify()
        self.mock_cb1.assert_called_once()
        self.mock_cb2.assert_called_once()

    @patch("pyinotify.Event")
    def test_paths_match(self, mock_event):
        mock_event.path = self.testpath2
        mock_event.pathname = self.testpath2
        self.assertTrue(self.dw3.paths_match(mock_event.path, mock_event.pathname))
        mock_event.pathname = "%s.swp" % self.testpath2
        self.assertFalse(self.dw3.paths_match(mock_event.path, mock_event.pathname))
        mock_event.pathname = self.testpath2
        mock_event.path = self.testpath1
        self.assertTrue(self.dw3.paths_match(mock_event.path, mock_event.pathname))
        mock_event.pathname = self.testpath1
        self.assertFalse(self.dw3.paths_match(mock_event.path, mock_event.pathname))

    @patch("pyinotify.Event")
    def test_file_modified(self, mock_event):
        mock_event.mask = 1
        self.assertFalse(self.dw3.file_modified(mock_event.mask))
        mock_event.mask = self.dw3.IN_MODIFY
        self.assertTrue(self.dw3.file_modified(mock_event.mask))
        mock_event.mask = self.dw3.IN_DELETE
        self.assertTrue(self.dw3.file_modified(mock_event.mask))
        mock_event.mask = self.dw3.IN_MOVED_TO
        self.assertTrue(self.dw3.file_modified(mock_event.mask))


class TestLoop:
    def __init__(self, fsw):
        self.stopped = False
        self.fsw = fsw

    def run(self):
        self.fsw.loop()
        self.stopped = True
