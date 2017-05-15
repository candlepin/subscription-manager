import tempfile
import shutil
import os

import mock

import fixture

from subscription_manager import file_monitor


class TestMonitorDirectory(fixture.SubManFixture):

    def setUp(self):
        super(TestMonitorDirectory, self).setUp()
        self.temp_dir = None

    def test(self):

        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp-file_monitor')
        md = file_monitor.MonitorDirectory(self.temp_dir)
        md.update()

        mtime = os.path.getmtime(self.temp_dir)

        # keep changing the temp dir until it's mtime changes
        while os.path.getmtime(self.temp_dir) == mtime:
            tf_h, _ = tempfile.mkstemp(dir=self.temp_dir)
            tf = os.fdopen(tf_h, 'w')
            tf.write("something")
            tf.close()

        changed_post = md.update()
        self.assertTrue(changed_post)

    def test_no_change(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp-file_monitor')
        md = file_monitor.MonitorDirectory(self.temp_dir)

        changed = md.update()
        self.assertFalse(changed)

        changed = md.update()
        self.assertFalse(changed)

    def test_check_mtime(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp-file_monitor')
        doesnt_exist = os.path.join(self.temp_dir, 'doesntexist')

        md = file_monitor.MonitorDirectory(doesnt_exist)
        mtime, exists = md._check_mtime()
        self.assertFalse(exists)

    def tearDown(self):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)


class TestMonitorDirectories(fixture.SubManFixture):
    def setUp(self):
        super(TestMonitorDirectories, self).setUp()
        self.temp_dir = None

    def test_empty_dir_list(self):
        fm = file_monitor.MonitorDirectories()
        fm.update()

    def test_callback(self):
        callback_result = []

        def changed_callback(result):
            callback_result.append(result)

        fm = file_monitor.MonitorDirectories(changed_callback=changed_callback)
        fm.update()
        self.assertEqual(callback_result, [])

    def test_from_path_list(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp-file_monitor')

        fm = file_monitor.MonitorDirectories.from_path_list(path_list=[self.temp_dir])
        fm.update()

    def test_mix_updates(self):
        mock_dir = file_monitor.MonitorDirectory("/not/a/real/path",
                                                 mock.MagicMock())
        mock_dir._check_mtime = mock.MagicMock(return_value=(123456, True))

        mock_dir_false = file_monitor.MonitorDirectory("/different/fake/path",
                                                       mock.MagicMock())
        mock_dir_false._check_mtime = mock.MagicMock(return_value=(452345345, True))

        def changed_callback():
            print "foo"

        fm = file_monitor.MonitorDirectories(dir_monitors=[mock_dir_false, mock_dir],
                                             changed_callback=changed_callback)
        fm.update()
        print "changed", mock_dir._changed_callback.called

    def tearDown(self):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
