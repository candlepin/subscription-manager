# Copyright (c) 2023 Red Hat, Inc.
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

import dbus
import logging

from rhsmlib.dbus.server import DomainSocketServer

from test import subman_marker_dbus
from test.fixture import SubManFixture

# Set DBus mainloop early in test run (test import time!)
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
log = logging.getLogger(__name__)


@subman_marker_dbus
class TestDomainSocketServer(SubManFixture):
    def test_unix_socket_invalid_path(self):
        server = DomainSocketServer()
        # force an unix socket in all the cases
        server._server_socket_iface = "unix:dir="
        # force an invalid path
        server._server_socket_path = "/i-dont-exists/really"
        with self.assertRaises(dbus.exceptions.DBusException):
            path = server.run()
            self.assertIsNotNone(path)
