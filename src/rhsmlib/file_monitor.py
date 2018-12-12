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

from rhsm.config import initConfig
from rhsmlib.services import config
from six.moves import configparser
import logging
import os.path
import fnmatch
import time

try:
    import pyinotify
except ImportError:
    pyinotify = None


log = logging.getLogger(__name__)
conf = config.Config(initConfig())


class FilesystemWatcher(object):
    """
    Watches a set of directories and notifies when there are changes

    Polling implementation
    Calls callbacks associated with directory when the directory changes
    Uses a loop running in its own thread
    ** Use create_filesystem_watcher to create an instance of a filesystem_watcher
    """
    def __init__(self, dir_watches):
        """
        :param dir_watches: list of directories to watch (see DirectoryWatch class below)
        """
        self.dir_watches = set(dir_watches)
        self.should_stop = False

    def stop(self):
        self.should_stop = True

    def update(self):
        """
        calls all callbacks in dir watches that have changed according to mtime
        :return: set of dir watches that have changed, for testing purposes
        """
        changed_dir_watches = self.changed_dw_set()
        for dir_watch in changed_dir_watches:
            dir_watch.notify()
        return changed_dir_watches  # returned a value for testing purposes (test_file_monitor.py)

    def get_mtime(self, dw):
        """
        :param dw: directory watch we are looking at
        :return: timestamp of directory watch we are looking at
        """
        try:
            timestamp = os.path.getmtime("%s" % dw.path)
        except OSError:
            timestamp = None
        return timestamp

    def changed_dw_set(self):
        """
        checks which dir watches out of dir watch list have changed according to mtime of path,
        updates dir watch timestamp if changed
        :return: set of changed dir watches
        """
        changed_dws = set()
        for dir_watch in self.dir_watches:
            timestamp = self.get_mtime(dir_watch)
            if dir_watch.timestamp != timestamp:
                changed_dws.add(dir_watch)
                dir_watch.timestamp = timestamp
        return changed_dws

    def loop(self, user_end_loop_cb=None):
        """
        Loops while self.should_stop is false and the callback() is not true

        Initializes timestamps for each dir watch in dir watch list, sets callback,
        notifies dir watch if it has changed
        :param user_end_loop_cb: callback function to be called at end of each iteration of the loop
        :return:
        """
        for dw in self.dir_watches:
            dw.timestamp = self.get_mtime(dw)
        while not end_loop_cb(self, user_callback=user_end_loop_cb):
            self.update()
            time.sleep(2.0)
        self.stop()


class InotifyFilesystemWatcher(FilesystemWatcher):
    """
    Watches a set of directories and notifies when there are changes

    Inotify implementation
    Calls callbacks associated with directory when the directory changes
    Uses a loop running in its own thread
    ** Use create_filesystem_watcher to create instance of filesystem watcher
    """
    def __init__(self, dir_watches):
        """
        Filesystem watcher if pyinotify is configured and available
        loop function will override parent class loop function
        :param dir_watches: list of directories to watch (see DirectoryWatch class below)
        """
        super(InotifyFilesystemWatcher, self).__init__(dir_watches)
        self.watch_manager = None
        self.notifier = None

    def loop(self, callback=None):
        """
        sets up watch manager, notifier, adds watches to watch manager, and starts loop
        :param callback: callback method to be called at the end of each iteration of the loop
        :return:
        """
        self.watch_manager = pyinotify.WatchManager()
        self.notifier = pyinotify.Notifier(self.watch_manager, self.handle_event)
        self.add_watches()

        def inotify_callback():
            return end_loop_cb(self, user_callback=callback)

        while not inotify_callback():
            self.notifier.process_events()
            if self.notifier.check_events(500):  # keeps tests reasonably fast while still timing out
                self.notifier.read_events()

    def handle_event(self, event):
        """
        default process function for pyinotify notifier
        :param event: pyinotify Event object, has path and mask of flags representing file modification
        :return:
        """
        for dir_watch in self.dir_watches:
            if dir_watch.paths_match(event.path, event.pathname) and dir_watch.file_modified(event.mask):
                dir_watch.notify()

    def add_watches(self):
        """
        adds watches to the watch manager
        :return:
        """
        for dir_watch in self.dir_watches:
            if dir_watch.is_file:
                # watch for any changes in the directory, but only be notified of the specific path
                dir_name = os.path.abspath(os.path.dirname(dir_watch.path))
                self.watch_manager.add_watch(dir_name, dir_watch.mask, self.handle_event, do_glob=dir_watch.is_glob)
            else:
                # is already directory
                self.watch_manager.add_watch(dir_watch.path, dir_watch.mask, self.handle_event, do_glob=dir_watch.is_glob)


class DirectoryWatch(object):
    """
    Directory to be watched

    Included in list to be passed into filesystem watcher object
    Example usage:
        directory_watch = DirectoryWatch("~/home/", [my_function1, my_function2])
    """
    def __init__(self, path, callbacks, is_glob=False):
        """
        :param path: path associated with directory to be watched
        :param callbacks: list of methods called when directory is changed
        :param is_glob: bool - if path provided is glob or not
        """
        self.IN_DELETE = 0x00000200
        self.IN_MODIFY = 0x00000002
        self.IN_MOVED_TO = 0x00000080

        self.path = os.path.abspath(path)
        self.is_file = not os.path.isdir(self.path)  # used isdir because if path does not exist, assumed to be file
        self.timestamp = None
        self.is_glob = is_glob
        self.callbacks = callbacks
        self.mask = self.IN_DELETE | self.IN_MODIFY | self.IN_MOVED_TO

    def notify(self):
        """
        calls all callbacks associated with dir watch
        :return:
        """
        for cb in self.callbacks:
            if cb is not None:
                try:
                    cb()
                except Exception as e:
                    log.exception(e)

    def paths_match(self, event_path, event_pathname):
        """
        checks if event path matches any of the dir watch paths associated to it
        :param event_path: path of the inotify event object
        :param event_pathname: pathname of the inotify event object
        see pyinotify event class for more info
        :return: bool - if paths match or not
        """
        event_pathname = os.path.realpath(event_pathname)
        event_path = os.path.realpath(event_path)
        if self.is_file:
            # we do not care about events on other paths, like .swp files
            return fnmatch.fnmatchcase(event_pathname, self.path)
        return fnmatch.fnmatchcase(event_path, self.path)

    def file_modified(self, event_mask):
        """
        checks if any flag has been set by event corresponding to modification
        :param event_mask: mask of the inotify event object, signifies what happened
        :return: bool - if any of the modification flags have been set
        """
        return bool(self.mask & event_mask)


def end_loop_cb(fsw, user_callback=None):
    if user_callback is not None:
        try:
            return user_callback() or fsw.should_stop
        except Exception as e:
            log.exception(e)
    return fsw.should_stop


def create_filesystem_watcher(dir_watches):
    """
    determines if inotify is available and configured in rhsm.conf
    If yes, uses pyinotify. Else, uses polling methods.
    Uses inotify by default
    :param dir_watches: list of directories to watch to create
    correct filesystem watcher object
    :return: correct filesystem watcher object

    Example usage:
        filesystem_watcher = create_filesystem_watcher([directory_watch1, directory_watch2])
        thread = threading.Thread(target=filesystem_watcher.loop)
        thread.start()
    """
    available = is_inotify_available()
    configed = is_inotify_config()
    if not (available and configed):
        return FilesystemWatcher(dir_watches)
    else:
        return InotifyFilesystemWatcher(dir_watches)


def is_inotify_available():
    return pyinotify is not None


def is_inotify_config():
    """
    Check if inotify is enabled or disabled in rhsm.conf.
    It is enabled by default.
    :return: It returns True, when inotify is enabled. Otherwise it returns False.
    """
    try:
        use_inotify = conf['rhsm'].get_int('inotify')
    except ValueError as e:
        log.exception(e)
        return True
    except configparser.Error as e:
        log.exception(e)
        return True
    else:
        if use_inotify is None:
            return True

    return bool(use_inotify)
