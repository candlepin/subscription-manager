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

Perfers to use gio as the backend, but can fallback to python-inotify.
"""

import gobject

try:
    import gio
    _use_gio = True
except ImportError, e:
    _use_gio = False

if _use_gio:

    class Monitor(gobject.GObject):

        __gsignals__ = {
            'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple())
        }

        def __init__(self, path):
            self.__gobject_init__()
            gio.File(path).monitor().connect('changed', self.on_file_change)

        def on_file_change(self, filemonitor, first_file, other_file,
                event_type):
            self.emit('changed')

else:

    import gobject
    import pyinotify


    class _EventHandler(pyinotify.ProcessEvent):

        def __init__(self):
            super(_EventHandler, self).__init__()

            # we can get multiple events during a given poll, but we only want
            # to signal once. so just set this flag, and the Monitor class can
            # handle it (then clear the flag)
            self.found_events = False

        def process_default(self, event):
            self.found_events = True


    class Monitor(gobject.GObject):

        __gsignals__ = {
            'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple())
        }


        def __init__(self, path):
            self.__gobject_init__()
            self._watch_manager = pyinotify.WatchManager()
            self._handler = _EventHandler()
            self._notifier = pyinotify.Notifier(self._watch_manager,
                    self._handler, timeout=10)

            mask = pyinotify.IN_CREATE | pyinotify.IN_DELETE | \
                    pyinotify.IN_DELETE_SELF | pyinotify.IN_MODIFY | \
                    pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | \
                    pyinotify.IN_MOVE_SELF
            self._watch_manager.add_watch(path, mask, rec=True)
            # same timeout as gio monitor, at time of writing.
            gobject.timeout_add(800, self._run_check)

        def _run_check(self):
            self._notifier.process_events()
            while self._notifier.check_events():
                self._notifier.read_events()
                self._notifier.process_events()

            if self._handler.found_events:
                self._handler.found_events = False
                self.emit("changed")
            return True
