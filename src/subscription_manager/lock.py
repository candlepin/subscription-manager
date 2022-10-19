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
    def __init__(self, path: str):
        self.path: str = path
        self.pid: Union[int, None] = None
        self.fp = None

    def open(self, blocking: bool = True) -> bool:
        """
        Try to open lock file, write PID to the lock file and finally lock the file.
        Note. This function could block whole process, when blocking is True (default behavior).
        Return True, when it was possible to open and lock the file. Otherwise, return False.
        """
        # First, try to create lock file, when it does not exist
        # Note: this part should raise
        if not self.exists():
            self.fp = open(self.path, "w")
            self.setpid()
            self.close()

        # Then try to lock the file
        try:
            self.fp = open(self.path, "r+")
            fd = self.fp.fileno()
            if blocking is True:
                fcntl.flock(fd, fcntl.LOCK_EX)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as err:
            log.debug(f"Unable to lock file {self.path}: {err}")
            return False
        else:
            return True

    def getpid(self) -> Union[int, None]:
        """
        Try to get PID from the locked file
        """
        if self.pid is None and self.fp is not None:
            content = self.fp.read().strip()
            if content:
                self.pid = int(content)
            else:
                return None
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
        pid = self.getpid()
        if pid is None:
            return status
        try:
            os.kill(pid, 0)
        except Exception as err:
            log.debug(f"Unable to send 0 signal to process {pid}: {err}")
        else:
            status = True
        return status

    def delete(self) -> None:
        """
        Try to delete lock file
        """
        if self.mypid() or not self.valid():
            self.close()
            try:
                os.unlink(self.path)
            except FileNotFoundError as err:
                log.debug(f"Unable to unlink file {self.path}, {err}")

    def close(self) -> None:
        """
        Try to close lock file
        """
        if self.fp is not None:
            fd = self.fp.fileno()
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception as err:
                log.debug(f"Unable to unlock file {self.path}: {err}")
            try:
                self.fp.close()
            except Exception as err:
                log.debug(f"Unable to close file {self.path}: {err}")
        self.pid = None
        self.fp = None

    def exists(self) -> bool:
        """
        Check if lock file already exists
        """
        return os.path.exists(self.path)

    def __del__(self):
        self.close()


class Lock(object):
    """
    Class encapsulating using of LockFile object
    """

    # Use mutex for locking this object to avoid race condition,
    # when threads are used. The subclass of Lock (ActionLock) is
    # used as a singleton
    mutex: Mutex = Mutex()

    def __init__(self, path: str):
        self.path: str = path
        self.lockdir: Union[str, None] = None
        self.depth: int = 0

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

    def acquire(self, blocking: bool = True) -> bool:
        """
        Try to acquire lock
        """
        log.debug(f"Locking file: {self.path} blocking: {blocking}")
        try:
            self.mutex.acquire()
            log.debug("Mutex acquired")
            lock_file = LockFile(self.path)
            if lock_file.mypid():
                log.debug(f"File: {self.path} is already locked by this process {lock_file.getpid()}")
                return True
            locked = lock_file.open(blocking=blocking)
            if locked is True:
                self.depth += 1
            else:
                log.debug(f"Unable to lock {self.path}")
        finally:
            self.mutex.release()
        log.debug(f"File {self.path} locked: {locked}")
        return locked

    def acquired(self) -> bool:
        """
        Return if the lock is locked or not
        """
        self.mutex.acquire()
        try:
            return self.depth > 0
        finally:
            self.mutex.release()

    def release(self) -> None:
        """
        Try to release lock
        """
        log.debug(f"Unlocking file: {self.path}")
        self.mutex.acquire()
        lock_file = LockFile(self.path)
        lock_file.delete()
        self.depth -= 1
        self.mutex.release()
        log.debug(f"File {self.path} unlocked")

    def __del__(self) -> None:
        """
        Make sure that lock is released, when the instance of
        object is destroyed
        """
        try:
            self.release()
        except Exception as err:
            log.debug(f"Unable to release lock: {err}")

    # def acquire(self, blocking=None):
    #     """Behaviour here is modeled after threading.RLock.acquire.
    #
    #     If 'blocking' is False, we return True if we didn't need to block, and we acquired the lock.
    #     We return False, if we couldn't acquire the lock and would have
    #     had to wait and block.
    #
    #     If 'blocking' is None, we return None when we acquire the lock, otherwise block until we do.
    #
    #     If 'blocking' is True, we behave the same as with blocking=None, except we return True.
    #
    #     """
    #
    #     if self.lockdir is None:
    #         return
    #     f = LockFile(self.path)
    #     try:
    #         try:
    #             while True:
    #                 # When blocking is True, then following f.open() could block the code
    #                 # until the file is locked
    #                 f.open(blocking=blocking)
    #                 f.getpid()
    #                 if f.mypid():
    #                     self.wait()
    #                     if blocking is not None:
    #                         return True
    #                     return
    #
    #                 if f.valid():
    #                     f.close()
    #                     # Note: blocking has three meanings for
    #                     # None, True, False, so 'not blocking' != 'blocking == False'
    #                     if blocking is False:
    #                         return False
    #                     time.sleep(LOCK_WAIT_DURATION)
    #                 else:
    #                     break
    #             self.wait()
    #             f.setpid()
    #         except OSError as e:
    #             log.exception(e)
    #             print("could not create lock")
    #     finally:
    #         f.close()
    #
    #     # if no blocking arg is passed, return nothing/None
    #     if blocking is not None:
    #         return True
    #     return None
    #
    # def release(self):
    #     if self.lockdir is None:
    #         return
    #     if not self.acquired():
    #         return
    #     self.signal()
    #     if self.acquired():
    #         return
    #     f = LockFile(self.path)
    #     try:
    #         f.open()
    #         f.delete()
    #     finally:
    #         f.close()
    #
    # def acquired(self):
    #     if self.lockdir is None:
    #         return
    #     # mutex = self.mutex
    #     # mutex.acquire()
    #     try:
    #         return self.depth > 0
    #     finally:
    #         pass
    #         # mutex.release()
    #
    # def wait(self) -> "Lock":
    #     # mutex = self.mutex
    #     # mutex.acquire()
    #     try:
    #         self.depth += 1
    #     finally:
    #         pass
    #         # mutex.release()
    #     return self
    #
    # def signal(self) -> None:
    #     # mutex = self.mutex
    #     # mutex.acquire()
    #     try:
    #         if self.acquired():
    #             self.depth -= 1
    #     finally:
    #         pass
    #         # mutex.release()
    #
    # def __del__(self):
    #     try:
    #         self.release()
    #     except Exception:
    #         pass


class ActionLock(Lock):
    """
    This class is used as singleton for locking actions related to certificates,
    because many processes tries to modify installed certificates. It can be subscription-manager,
    but there are many services trying to access/modify installed certificates (rhsmcertd, rhsm)
    and maybe some other apps too.
    """

    # Default lock file
    PATH = "/run/rhsm/cert.pid"

    # Fallback path, when it is not possible to write to default file (e.g. when buildah is used)
    # and root directory / is mounted as read-only.
    USER_PATH = "{XDG_RUNTIME_DIR}/rhsm/cert.pid"

    # When XDG_RUNTIME_DIR environment variable is not set, then try to use convention
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
            # The XDG_RUNTIME_DIR environment variable is not defined in
            # some cases (typically, when sudo is used)
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


def _main():
    """Smoke testing of locking lock file"""
    print("Creating lock object...")
    my_lock = Lock("/tmp/my_lock.lock")
    print("Locking lock file: {my_lock.fd}...")
    res = my_lock.acquire(blocking=True)
    print(f"Locked: {res}")
    if res is True:
        try:
            print("Waiting 60 seconds...")
            time.sleep(60)
        except KeyboardInterrupt:
            print("Interrupted by keyboard")
        else:
            print("Releasing lock file due to timeout")
        finally:
            my_lock.release()

    # print("Creating lock file object...")
    # lock_file = LockFile("/tmp/my_lock.lock")
    # print(f"Locking lock file: {lock_file.fp}...")
    # lock_file.open(blocking=True)
    # try:
    #     print("Waiting 60 seconds...")
    #     time.sleep(60)
    # finally:
    #     print("Releasing lock file")
    #     lock_file.close()


if __name__ == '__main__':
    _main()
