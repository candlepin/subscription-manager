from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
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

"""
Watch for and be notified of changes in a file.
"""
from copy import copy
import fnmatch
import os
import time


class MonitorDirectory(object):

    def __init__(self, path, changed_callback=None):
        self.mtime = None
        self.exists = None
        self.path = path
        self._changed_callback = changed_callback
        self.update()

    def _check_mtime(self):
        mtime = 0
        try:
            mtime = self._get_mtime(self.path)
            exists = True
        except OSError:
            exists = False
        return (mtime, exists)

    def _get_mtime(self, path):
        return os.path.getmtime(path)

    def _on_changed(self):
        if self._changed_callback:
            self._changed_callback()

    def _changed(self, mtime, mtime2, exists, exists2):
        return mtime != mtime2 or exists != exists2

    def update(self):
        mtime, exists = self._check_mtime()

        # Has something changed?
        result = self._changed(mtime, self.mtime, exists, self.exists)

        # Update saved values
        self.mtime = mtime
        self.exists = exists

        if result:
            self._on_changed()

        return result


class FilesystemWatcher:
    def __init__(self, dir_watches=None, end_loop_cb=None):
        self.dir_watches = dir_watches or []
        self.end_loop_cb = end_loop_cb or self.__default_end_loop_cb
        self.built = False  # Whether this instance is no longer modifiable
        self.timeout = 2000  # Milliseconds to sleep between updates
        self.sleep = self._sleep
        self.update = self.__noop
        self.stop = self.__noop

    @staticmethod
    def _to_dir_watch(item):
        if isinstance(item, DirectoryWatch):
            return item
        elif isinstance(item, tuple):
            return DirectoryWatch(*item)

    def add_watch(self, watch):
        self._raise_if(self.built)
        item = self._to_dir_watch(watch)
        if item:
            self.dir_watches.append(item)
        return self

    def add_watches(self, watches):
        self._raise_if(self.built)
        for item in watches:
            self.add_watch(item)
        return self

    def with_inotify(self):
        """
        Sets this FilesystemWatcher up to use inotify.
        Should be called only after done configuring the watcher.
        :return: The modified FilesystemWatcher
        """
        self._raise_if(self.built)

        def process_event(event):
            for dir_watch in self.dir_watches:
                if dir_watch.match_path(event.pathname) and dir_watch.match_mask(event.mask):
                    dir_watch.notify()

        import pyinotify
        from rhsmlib.dbus import inotify
        watch_manager = pyinotify.WatchManager()

        # Create custom event handler
        # Create notifier with timeout (one second).
        notifier = inotify.Notifier(watch_manager, process_event, timeout=1000)
        for watch in self.dir_watches:
            # Start to watch for events in directory with certificates of consumer
            watch_manager.add_watch(watch.path, watch.mask, do_glob=watch.glob, rec=False)

        self.update = lambda: notifier.update()
        self.sleep = lambda: notifier.sleep()
        self.stop = lambda: notifier.stop()
        self.built = True
        return self

    def without_inotify(self):
        """
        Sets this FilesystemWatcher up without inotify.
        Should be called only after done configuring the watcher.
        :return: The modified FilesystemWatcher
        """
        self._raise_if(self.built)
        dir_mon = MonitorDirectories.from_dir_watches(self.dir_watches)
        self.update = lambda: dir_mon.update()
        self.built = True
        return self

    def loop(self, callback=None):
        self._raise_if(not self.built)

        if callback:
            self.end_loop_cb = callback
        try:
            while True:
                self.update()
                if self.end_loop_cb():
                    break
                self.sleep()
        finally:
            self.stop()


    def _raise_if(self, condition, exception=ValueError, msg="Invalid usage, Watcher already built"):
        if condition:
            raise exception(msg)

    def _sleep(self):
        time.sleep(self.timeout / 1000)

    def __default_end_loop_cb(self):
        return False

    def __noop(self):
        pass


class MonitorDirectories(object):

    def __init__(self, dir_monitors=None, changed_callback=None):
        """Attach a timer callback to call run_check to poll periodically."""
        self.dir_monitors = dir_monitors or []
        self._changed_callback = changed_callback

    def update(self):
        # check all the dirs in a batch, to hopefully coalesce
        # related changes into one callback.

        results = [dir_monitor.update() for dir_monitor in self.dir_monitors]

        # If something has changed
        if True in results:
            self._on_changed()

        return True

    def _on_changed(self):
        if self._changed_callback:
            self._changed_callback()

    @classmethod
    def from_path_list(cls, path_list=None, changed_callback=None):
        dir_monitors = [MonitorDirectory(path) for path in path_list]
        return cls(dir_monitors=dir_monitors,
                   changed_callback=changed_callback)

    @classmethod
    def from_dir_watches(cls, watches=None, changed_callback=None):
        dir_monitors = [MonitorDirectory(watch.path, watch.changed_cb) for watch in watches]
        return cls(dir_monitors=dir_monitors,
                   changed_callback=changed_callback)


class DirectoryWatch(object):
    """
    Represents a path (or glob of paths) to watch along with a set of methods to be called when
    there has been a change to one of the files on the path.
    """
    # Constants shared with pyinotify
    IN_CREATE = 0x00000100
    IN_DELETE = 0x00000200
    IN_MODIFY = 0x00000002

    def __init__(self, path, cbs=None, changed_cb=None, mask=None, glob=False):
        """
        :param path: The path to be watched, should be a path to a directory or file or glob
        :type path: str
        :param changed_cb: the method to call when there are changes
          defaults to the self.notify method (calls all callbacks in self.callbacks
        :type changed_cb: callable
        :param mask: An integer mask representing the actions
        :param glob:
        """
        self.path = path
        self.glob = glob
        self.mask = mask or (DirectoryWatch.IN_CREATE | DirectoryWatch.IN_DELETE | DirectoryWatch.IN_MODIFY)
        self.callbacks = set(cbs) if cbs else set()
        self.changed_cb = changed_cb or self.notify

    def match_path(self, path):
        """
        Returns True if the path should be considered part of this DirectoryWatch
        :param path: The path under consideration
        :rtype: bool
        """
        if not self.glob:
            return os.path.commonprefix([path, self.path]) == self.path
        else:
            return fnmatch.fnmatch(path, self.path)

    def match_mask(self, mask):
        """
        Returns True if the given mask matches (at least in part) this DirectoryWatch
        :param mask: Integer representing the categories under consideration
        :rtype: bool
        """
        return bool(self.mask & mask)

    def notify(self):
        for cb in copy(self.callbacks):
            cb()