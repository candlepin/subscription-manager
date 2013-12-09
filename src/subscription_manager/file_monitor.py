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

import rhsm.config


class Monitor(gobject.GObject):

    __gsignals__ = {
        'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
            (gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN))
    }

    def __init__(self):
        self.__gobject_init__()
        cfg = rhsm.config.initConfig()
        # Identity, Entitlements, Products
        self.dirs = {cfg.get('rhsm', 'consumerCertDir'): None,
                cfg.get('rhsm', 'entitlementCertDir'): None,
                cfg.get('rhsm', 'productCertDir'): None}

        for directory in self.dirs:
            self.dirs[directory] = self._check_mtime(directory)

        # poll every 2 seconds for changes
        gobject.timeout_add(2000, self.run_check)

    def _check_mtime(self, path):
        mtime = 0
        try:
            mtime = os.path.getmtime(path)
            exists = True
        except OSError:
            exists = False

        return (mtime, exists)

    def run_check(self):
        result = []
        for directory in self.dirs:
            (mtime, exists) = self._check_mtime(directory)
            result.append((mtime != self.dirs[directory][0]) or
                    (exists != self.dirs[directory][1]))
            self.dirs[directory] = (mtime, exists)

        # If something has changed
        if True in result:
            self.emit("changed", *result)
        return True
