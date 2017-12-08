from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import subprocess
import sys
import shutil
import tempfile
import threading
import time

from nose import SkipTest

from subscription_manager import lock


class TestLock(unittest.TestCase):
    lf_name = "lock.file"

    def setUp(self):
        self.other_process = None

    def _lock_path(self):
        tmp_dir = tempfile.mkdtemp(suffix="-lock", prefix="subman-unit-tests-")
        self.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)
        return os.path.join(tmp_dir, self.lf_name)

    # For thread.Timer()
    def _kill_other_process(self, other_process):
        self.fail("nothing happened before we timed out.")
        # die die die
        other_process.terminate()
        other_process.kill()
        self.timer.cancel()

    def _grab_lock_from_other_pid(self, lockfile_path,
                                  other_process_timeout=None,
                                  acquire_timeout=None):
        # klugey
        other_process_timeout = other_process_timeout or 3.0
        acquire_timeout = acquire_timeout or 5.0

        sys_path = os.path.join(os.path.dirname(__file__), "../src")
        self.other_process = subprocess.Popen([sys.executable, __file__, lockfile_path],
                                              close_fds=True,
                                              stdin=subprocess.PIPE,
                                               env={'PYTHONPATH': sys_path})

        # make sure other process has had time to create the lock file
        while True:
            lock_exists = os.path.exists(lockfile_path)
            if lock_exists:
                break
            time.sleep(0.05)

        # in another thread, wait 3 seconds, then send 'whatever' to stdin of
        # other process so it closes. A timeout...
        def wait_for_pid(timer):
            time.sleep(other_process_timeout)
            self.close_lock_holder()
            timer.cancel()

        timer = threading.Timer(acquire_timeout, self.timeout_fail)

        op_thread = threading.Thread(target=wait_for_pid, args=[timer])
        op_thread.start()

        return op_thread

    def close_lock_holder(self):
        try:
            self.other_process.communicate("whatever".encode('utf-8'))
        except Exception as e:
            print(e)
            # whatever, we closed it in the other thread

    def timeout_fail(self):
        self.close_lock_holder()
        self.fail("timeoutsdfsdf")

    def test_two_pids_blocking_none_blocks(self):
        # This test will either fail occasionally, or have to wait an
        # unreasonable time period, which just slows down the test suite.
        # Left in code since it is a useful test if changing lock behavior,
        # but too troublesome in general.
        skip_test = True
        if skip_test:
            raise SkipTest('Skipping lock.test_two_pids_blocking_none_blocks')

        lock_path = self._lock_path()
        # start a different proc that holds the lock, that times out after 3
        self._grab_lock_from_other_pid(lock_path, 1.0, 0.2)

        b = lock.Lock(lock_path)

        res = b.acquire()
        self.assertTrue(res is None)

    def test_two_pids_blocking_none(self):
        lock_path = self._lock_path()
        # start a different proc that holds the lock, that times out after 3
        self._grab_lock_from_other_pid(lock_path, 0.2, 1.0)

        b = lock.Lock(lock_path)
        res = b.acquire()
        self.assertTrue(b.acquired())
        self.assertTrue(res is None)

    def test_two_pids_blocking_true(self):
        lock_path = self._lock_path()
        # start a different proc that holds the lock, that times out after 3
        self._grab_lock_from_other_pid(lock_path, 0.2, 1.0)
        b = lock.Lock(lock_path)
        res = b.acquire(blocking=True)
        self.assertTrue(b.acquired())
        self.assertTrue(res)

    def test_two_pids_blocking_false(self):
        lock_path = self._lock_path()
        self._grab_lock_from_other_pid(lock_path, 0.2, 1.0)
        b = lock.Lock(lock_path)
        res = b.acquire(blocking=False)
        self.assertFalse(b.acquired())
        self.other_process.communicate("whatever".encode('utf-8'))
        self.assertFalse(res)

    def test_lock(self):
        lock_path = self._lock_path()
        lf = lock.Lock(lock_path)
        self.assertEqual(lf.path, lock_path)
        self.assertEqual(lf.depth, 0)

    def test_lock_acquire(self):
        lock_path = self._lock_path()
        lf = lock.Lock(lock_path)
        res = lf.acquire()
        # given no args, acquire() blocks or returns None
        self.assertEqual(res, None)

    def test_lock_acquire_blocking_true(self):
        lock_path = self._lock_path()
        lf = lock.Lock(lock_path)
        res = lf.acquire(blocking=True)
        # acquire(blocking=True) will block or return True
        self.assertTrue(res)

    def test_lock_acquire_blocking_false(self):
        lock_path = self._lock_path()
        lf = lock.Lock(lock_path)
        res = lf.acquire(blocking=False)

        # res of False indicates lock could not be acquired without blocking
        # True indicates lock was acquired
        self.assertTrue(res)

    def test_lock_release(self):
        lock_path = self._lock_path()
        lf = lock.Lock(lock_path)
        lf.acquire()
        lf.release()

    def _stale_lock(self):
        lock_path = self._lock_path()
        fakepid = 123456789
        f = open(lock_path, 'w')
        f.write('%s\n' % fakepid)
        f.close()
        return lock_path

    def test_lock_acquire_stale_pid(self):
        lock_path = self._stale_lock()
        lf = lock.Lock(lock_path)
        res = lf.acquire(blocking=True)
        self.assertTrue(res)

    def test_lock_acquire_stale_pid_nonblocking(self):
        lock_path = self._stale_lock()
        lf = lock.Lock(lock_path)
        res = lf.acquire(blocking=False)
        self.assertTrue(res)

# always blocks, needs eventloop/threads
#    def test_lock_drive_full_blocking(self):
#        lock_path = "/dev/full"
#        lf = lock.Lock(lock_path)
#        res = lf.acquire(blocking=True)
#        log.debug(res)

# FIXME: the lockfile creation fails on /dev/full
#    def test_lock_drive_full_nonblocking(self):
#        lock_path = "/dev/full"
#        lf = lock.Lock(lock_path)
#        res = lf.acquire(blocking=False)
#        self.assertFalse(res)


# run this module's main in a subprocess to grab a lock from a different
# pid.
def main(args):
    lock_file_path = args[1]
    test_lock = lock.Lock(lock_file_path)

    # could return a useful value, so the thread communicating with
    # it could notice it couldn't get the lock
    res = test_lock.acquire(blocking=False)
    if res is False:
        return 128

    # exit on any stdin input
    for line in sys.stdin.readlines():
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[:]))
