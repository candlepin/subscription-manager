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
import tempfile
from threading import RLock as Mutex
import time
from typing import Union

import logging

log = logging.getLogger(__name__)

# how long to sleep before rechecking if we can
# acquire the lock.
LOCK_WAIT_DURATION = 0.5


class LockFile(object):
    def __init__(self, path):
        self.path = path
        self.pid = None
        self.fp = None

    def open(self) -> None:
        """
        Try to open lock file, write PID to the lock file and finally lock the file
        """
        if self.notcreated():
            self.fp = open(self.path, "w")
            self.setpid()
            self.close()
        self.fp = open(self.path, "r+")
        fd = self.fp.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)

    def getpid(self) -> Union[int, None]:
        """
        Try to get PID from the locked file
        """
        if self.pid is None and self.fp is not None:
            try:
                content = self.fp.read().strip()
            except PermissionError as err:
                log.error(f"Unable to get PID from file {self.path}: {err}")
            else:
                if content:
                    self.pid = int(content)
        return self.pid

    def setpid(self) -> None:
        """
        Try to set PID. When the self.fp is not set, then exception is raised.
        """
        self.fp.seek(0)
        content = str(os.getpid())
        self.fp.write(content)
        self.fp.flush()

    def mypid(self) -> bool:
        """
        If the PID in the locked file is PID of current process, then return True.
        Otherwise, return False.
        """
        return os.getpid() == self.getpid()

    def valid(self) -> bool:
        """
        Check if the process with PID is still running
        """
        status = False
        try:
            os.kill(self.getpid(), 0)
        except Exception as err:
            log.debug(f"Unable to send 0 signal to process: {err}")
        else:
            status = True
        return status

    def delete(self) -> None:
        """
        Try to delete lock file
        """
        if self.mypid() or not self.valid():
            self.close()
            os.unlink(self.path)

    def close(self) -> None:
        """
        Try to close lock file
        """
        try:
            fd = self.fp.fileno()
            fcntl.flock(fd, fcntl.LOCK_UN)
            self.fp.close()
        except Exception as err:
            log.debug(f"Unable to close file {self.path}: {err}")
        self.pid = None
        self.fp = None

    def notcreated(self) -> bool:
        """
        Check if lock file already exists
        """
        return not os.path.exists(self.path)

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
            else:
                # When lock directory exists, then check if the owner is
                # the same as current user. Otherwise, try to create some temporary
                # file to check if user can write to given directory. When the
                # file system is mounted as read-only, then root cannot write to
                # the directory despite it is super-user. In that case exception
                # PermissionError will be raised.
                if os.getuid() != os.stat(lock_dir).st_uid:
                    temp_file = tempfile.NamedTemporaryFile(dir=lock_dir)
                    temp_file.close()
        except PermissionError as err:
            log.info(f"Unable to create lock/write to directory {lock_dir}: {err}")
            raise err
        except Exception as err:
            log.debug(f"Unable to create lock directory {lock_dir}: {err}")
            self.lockdir = None
        else:
            self.lockdir = lock_dir

    def acquire(self, blocking=None):
        """Behaviour here is modeled after threading.RLock.acquire.

        If 'blocking' is False, we return True if we didn't need to block, and we acquired the lock.
        We return False, if we couldn't acquire the lock and would have
        had to wait and block.

        If 'blocking' is None, we return None when we acquire the lock, otherwise block until we do.

        If 'blocking' is True, we behave the same as with blocking=None, except we return True.

        """

        if self.lockdir is None:
            return
        f = LockFile(self.path)
        try:
            try:
                while True:
                    if f.open() is False:
                        break
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
            return self.depth > 0
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

    PATH = "/run/rhsm/cert.pid"

    USER_PATH = "{XDG_RUNTIME_DIR}/rhsm/cert.pid"

    USER_RUNTIME_DIR = "/run/user/{uid}"

    def __init__(self) -> None:
        try:
            super(ActionLock, self).__init__(self.PATH)
        except PermissionError:
            # When it is not possible to create lock in standard directory, then
            # try to use one in user directory
            user_path = self._get_user_lock_dir()
            if user_path is not None:
                super(ActionLock, self).__init__(user_path)
            else:
                log.error("Unable to create lock directory in user runtime directory")

    def _get_user_lock_dir(self) -> Union[None, str]:
        """
        Try to get lock directory in user runtime directory (typically /run/user/${UID}/)
        """
        if "XDG_RUNTIME_DIR" not in os.environ:
            log.debug("Environment variable XDG_RUNTIME_DIR not defined")
            log.debug("Trying to get user runtime directory from UID")
            uid = os.getuid()
            user_runtime_dir = self.USER_RUNTIME_DIR.format(uid=uid)
            if os.path.isdir(user_runtime_dir) is True:
                user_path = self.USER_PATH.format(XDG_RUNTIME_DIR=user_runtime_dir)
            else:
                log.warning(f"Directory {user_runtime_dir} does not exist")
                return None
        else:
            xdg_runtime_dir = os.environ["XDG_RUNTIME_DIR"]
            user_path = self.USER_PATH.format(XDG_RUNTIME_DIR=xdg_runtime_dir)
        log.info(f"Trying to use user lock directory: {user_path} (influenced by $XDG_RUNTIME_DIR)")
        return user_path
