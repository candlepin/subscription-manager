import unittest

from subscription_manager.gui import progress


class TestProgress(unittest.TestCase):
    def setUp(self):
        self.pw = progress.Progress("test title", "this is a test label")

    def test_set_progress_0(self):
        self.pw.set_progress(0, 100)

    def test_set_progress_0_0(self):
        self.pw.set_progress(0, 0)

    def test_set_progress_100(self):
        self.pw.set_progress(100, 100)

    def test_set_progress_100_0(self):
        self.pw.set_progress(100, 0)

    def test_set_progress_100_50(self):
        self.pw.set_progress(100, 50)

    def test_pulse(self):
        self.pw.pulse()

    def test_hide(self):
        self.pw.hide()

    def test_set_progress_label(self):
        self.pw.set_status_label("Hey, I'm a status label")
