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

Perfers to use gio as the backend, but can fallback to polling.
"""

import gobject
import os


class Monitor(gobject.GObject):

    __gsignals__ = {
        'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple())
    }

    def __init__(self, path):
        self.__gobject_init__()

        self._path = path

        (mtime, exists) = self._check_mtime()
        self._last_mtime = mtime
        self._exists = exists

        # poll every 2 seconds for changes
        gobject.timeout_add(2000, self._run_check)

    def _check_mtime(self):
        mtime = 0
        try:
            mtime = os.path.getmtime(self._path)
            exists = True
        except OSError:
            exists = False

        return (mtime, exists)

    def _run_check(self):
        (mtime, exists) = self._check_mtime()

        if (mtime != self._last_mtime) or (exists != self._exists):
            self.emit("changed")

        self._last_mtime = mtime
        self._exists = exists

        return True
