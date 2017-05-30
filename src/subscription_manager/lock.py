from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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
import fcntl
import os
from threading import RLock as Mutex
import time

# how long to sleep before rechecking if we can
# acquire the lock.
LOCK_WAIT_DURATION = 0.5

import logging
log = logging.getLogger(__name__)


class LockFile(object):

    def __init__(self, path):
        self.path = path
        self.pid = None
        self.fp = None

    def open(self):
        if self.notcreated():
            self.fp = open(self.path, 'w')
            self.setpid()
            self.close()
        self.fp = open(self.path, 'r+')
        fd = self.fp.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)

    def getpid(self):
        if self.pid is None:
            content = self.fp.read().strip()
            if content:
                self.pid = int(content)
        return self.pid

    def setpid(self):
        self.fp.seek(0)
        content = str(os.getpid())
        self.fp.write(content)
        self.fp.flush()

    def mypid(self):
        return (os.getpid() == self.getpid())

    def valid(self):
        status = False
        try:
            os.kill(self.getpid(), 0)
            status = True
        except Exception:
            pass
        return status

    def delete(self):
        if self.mypid() or not self.valid():
            self.close()
            os.unlink(self.path)

    def close(self):
        try:
            fd = self.fp.fileno()
            fcntl.flock(fd, fcntl.LOCK_UN)
            self.fp.close()
        except Exception:
            pass
        self.pid = None
        self.fp = None

    def notcreated(self):
        return (not os.path.exists(self.path))

    def __del__(self):
        self.close()


class Lock(object):

    mutex = Mutex()

    def __init__(self, path):
        self.depth = 0
        self.path = path
        self.lockdir = None
        self.blocking = None

        lock_dir, _fn = os.path.split(self.path)
        try:
            if not os.path.exists(lock_dir):
                os.makedirs(lock_dir)
            self.lockdir = lock_dir
        except Exception:
            self.lockdir = None

    def acquire(self, blocking=None):
        """Behaviour here is modeled after threading.RLock.acquire.

        If 'blocking' is False, we return True if we didn't need to block and we acquired the lock.
        We return False if couldn't acquire the lock and would have
        had to wait and block.

        if 'blocking' is None, we return None when we acquire the lock, otherwise block until we do.

        if 'blocking' is True, we behave the same as with blocking=None, except we return True.

        """

        if self.lockdir is None:
            return
        f = LockFile(self.path)
        try:
            try:
                while True:
                    f.open()
                    f.getpid()
                    if f.mypid():
                        self.P()
                        if blocking is not None:
                            return True
                        return

                    if f.valid():
                        f.close()
                        # Note: blocking has three meanings for
                        # None, True, False, so 'not blocking' != 'blocking == False'
                        if blocking is False:
                            return False
                        time.sleep(LOCK_WAIT_DURATION)
                    else:
                        break
                self.P()
                f.setpid()
            except OSError as e:
                log.exception(e)
                print("could not create lock")
        finally:
            f.close()

        # if no blocking arg is passed, return nothing/None
        if blocking is not None:
            return True
        return None

    def release(self):
        if self.lockdir is None:
            return
        if not self.acquired():
            return
        self.V()
        if self.acquired():
            return
        f = LockFile(self.path)
        try:
            f.open()
            f.delete()
        finally:
            f.close()

    def acquired(self):
        if self.lockdir is None:
            return
        mutex = self.mutex
        mutex.acquire()
        try:
            return (self.depth > 0)
        finally:
            mutex.release()

    # P
    def wait(self):
        mutex = self.mutex
        mutex.acquire()
        try:
            self.depth += 1
        finally:
            mutex.release()
        return self
    P = wait

    # V
    def signal(self):
        mutex = self.mutex
        mutex.acquire()
        try:
            if self.acquired():
                self.depth -= 1
        finally:
            mutex.release()
    V = signal

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass


class ActionLock(Lock):

    PATH = '/var/run/rhsm/cert.pid'

    def __init__(self):
        super(ActionLock, self).__init__(self.PATH)
