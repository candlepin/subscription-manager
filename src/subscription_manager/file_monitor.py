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
import os


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
