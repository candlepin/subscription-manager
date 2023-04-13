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
from typing import Union, Optional, TextIO

import logging

log = logging.getLogger(__name__)

# how long to sleep before rechecking if we can
# acquire the lock.
LOCK_WAIT_DURATION: float = 0.5


class LockFile:
    def __init__(self, path: str):
        self.path: str = path
        self.pid: Optional[int] = None
        self.fp: Optional[TextIO] = None

    def open(self, blocking: bool = False) -> None:
        """
        Try to open lock file, write PID to the lock file and finally lock the file
        :param blocking: When it is set to True, then file locking blocks
        """
        if self.notcreated():
            self.fp = open(self.path, "w")
            self.setpid()
            self.close()
        self.fp = open(self.path, "r+")
        fd: int = self.fp.fileno()
        if blocking is True:
            fcntl.flock(fd, fcntl.LOCK_EX)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def getpid(self) -> Union[int, None]:
        """
        Try to get PID from the locked file
        """
        if self.pid is None and self.fp is not None:
            content: str = self.fp.read().strip()
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
        status: bool = False
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
        if self.fp is None:
            self.pid = None
            return
        try:
            fd: int = self.fp.fileno()
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception as err:
            log.debug(f"Unable to unlock file {self.path}: {err}")
        try:
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

    def __del__(self) -> None:
        self.close()


class Lock:
    mutex = Mutex()

    def __init__(self, path: str):
        self.depth: int = 0
        self.path: str = path
        self.lockdir: Optional[str] = None
        self.blocking: Optional[bool] = None

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

    # FIXME: Following code is absolutely stochastic and there has to be some black magic, because
    # it is miracle that it works and it does not block any application using this code.
    # It seems that nothing uses blocking keyed argument. Thus only default equal None is used.
    def acquire(self, blocking: Optional[bool] = None) -> Optional[bool]:
        """Behaviour here is modeled after threading.RLock.acquire.

        If 'blocking' is False, we return True if we didn't need to block, and we acquired the lock.
        We return False, if we couldn't acquire the lock and would have
        had to wait and block.

        If 'blocking' is None, we return None when we acquire the lock, otherwise block until we do.

        If 'blocking' is True, we behave the same as with blocking=None, except we return True.

        """

        if self.lockdir is None:
            return None
        f = LockFile(self.path)
        log.debug(f"Locking file: {self.path}")
        try:
            try:
                while True:
                    # FIXME: if you set blocking to True, then this code would work anyway.
                    # It is absolutely unclear, how it is possible, because fcntl.flock()
                    # should block in this case. The blocking is set to False here to be sure
                    # that the code will be still functional, when the magic would be over.
                    f.open(blocking=False)
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
                log.exception(f"Could not lock file: {self.path}", exc_info=e)
        finally:
            f.close()

        # if no blocking arg is passed, return nothing/None
        if blocking is not None:
            return True
        return None

    def release(self) -> None:
        if self.lockdir is None:
            return
        if not self.acquired():
            return
        self.V()
        if self.acquired():
            return
        log.debug(f"Unlocking file {self.path}")
        f = LockFile(self.path)
        try:
            # FIXME: it does not make any sense to try to lock file again here
            f.open()
            f.delete()
        finally:
            f.close()

    def acquired(self) -> Optional[bool]:
        if self.lockdir is None:
            return
        mutex = self.mutex
        mutex.acquire()
        try:
            return self.depth > 0
        finally:
            mutex.release()

    # P
    def wait(self) -> "Lock":
        mutex = self.mutex
        mutex.acquire()
        try:
            self.depth += 1
        finally:
            mutex.release()
        return self

    P = wait

    # V
    def signal(self) -> None:
        mutex = self.mutex
        mutex.acquire()
        try:
            if self.acquired():
                self.depth -= 1
        finally:
            mutex.release()

    V = signal

    def __del__(self) -> None:
        try:
            self.release()
        except Exception:
            pass


class ActionLock(Lock):
    # Standard path of lock file
    PATH = "/run/rhsm/cert.pid"

    # This path is used, when standard directory is read-only and environment
    # variable XDG_RUNTIME_DIR is defined
    USER_PATH = "{XDG_RUNTIME_DIR}/rhsm/cert.pid"

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
        if "XDG_RUNTIME_DIR" in os.environ:
            xdg_runtime_dir = os.environ["XDG_RUNTIME_DIR"]
            user_path = self.USER_PATH.format(XDG_RUNTIME_DIR=xdg_runtime_dir)
        else:
            log.debug("Environment variable XDG_RUNTIME_DIR not defined")
            return None
        log.info(f"Trying to use user lock directory: {user_path} (influenced by $XDG_RUNTIME_DIR)")
        return user_path
