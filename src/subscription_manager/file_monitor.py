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

#from gi.repository import GObject
#from gi.repository import GLib
from subscription_manager import ga

import os

import rhsm.config


class MonitorDirectory(object):

    def __init__(self, path):
        self.mtime = None
        self.exists = None
        self.path = path
        self.update()

    def _check_mtime(self):
        mtime = 0
        try:
            mtime = os.path.getmtime(self.path)
            exists = True
        except OSError:
            exists = False
        return (mtime, exists)

    def update(self):
        mtime, exists = self._check_mtime()

        # Has something changed?
        result = mtime != self.mtime or exists != self.exists

        # Update saved values
        self.mtime = mtime
        self.exists = exists

        return result


class Monitor(ga.GObject.GObject):

    __gsignals__ = {
        'changed': (ga.GObject.SignalFlags.RUN_LAST, None,
            (ga.GObject.TYPE_BOOLEAN, ga.GObject.TYPE_BOOLEAN, ga.GObject.TYPE_BOOLEAN))
    }

    def __init__(self):
        #self.__gobject_init__()
        ga.GObject.GObject.__init__(self)
        cfg = rhsm.config.initConfig()
        # Identity, Entitlements, Products
        self.dirs = [MonitorDirectory(cfg.get('rhsm', 'consumerCertDir')),
                MonitorDirectory(cfg.get('rhsm', 'entitlementCertDir')),
                MonitorDirectory(cfg.get('rhsm', 'productCertDir'))]

        # poll every 2 seconds for changes
        ga.GLib.timeout_add(2000, self.run_check)

    def run_check(self):
        result = [directory.update() for directory in self.dirs]

        # If something has changed
        if True in result:
            self.emit("changed", *result)
        return True
