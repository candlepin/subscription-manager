import unittest
import tempfile

from subscription_manager import lock


class TestLock(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def test_lock(self):
        lf = lock.Lock("%s/lock.file" % self.tmp_dir)

    def test_lock_acquire(self):
        lf = lock.Lock("%s/lock.file" % self.tmp_dir)
        lf.acquire()

    def test_lock_release(self):
        lf = lock.Lock("%s/lock.file" % self.tmp_dir)
        lf.acquire()
        lf.release()

        
