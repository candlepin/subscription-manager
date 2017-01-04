# Copyright (c) 2016 Red Hat, Inc.
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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import dbus
import mock

from rhsmlib.dbus import service_wrapper, constants


class ServiceWrapperTest(unittest.TestCase):
    def test_parse_argv(self):
        opts, args = service_wrapper.parse_argv(
            ['cmd_name', '--verbose', '--bus-name', 'Hello', 'Foo'], 'Default')
        self.assertTrue(opts.verbose)
        self.assertEqual(opts.bus_name, 'Hello')
        self.assertEqual(args, ['Foo'])

    def test_uses_default_bus_name(self):
        opts, args = service_wrapper.parse_argv(['cmd_name', 'Foo'], 'Default')
        self.assertFalse(opts.verbose)
        self.assertEqual(opts.bus, dbus.SystemBus)
        self.assertEqual(opts.bus_name, 'Default')
        self.assertEqual(args, ['Foo'])

    def test_loads_bus_given(self):
        opts, args = service_wrapper.parse_argv(['cmd_name', '--bus', 'dbus.SessionBus', 'Foo'], 'Default')
        self.assertEqual(opts.bus, dbus.SessionBus)

    @mock.patch("rhsmlib.dbus.service_wrapper.server.Server")
    def test_loads_an_object_class(self, mock_serve):
        # Just use some class we have available
        service_wrapper.main(['cmd_name', 'mock.MagicMock'])
        mock_serve.assert_called_with(
            bus_class=dbus.SystemBus,
            bus_name=constants.BUS_NAME,
            object_classes=[mock.MagicMock]
        )

    @mock.patch("rhsmlib.dbus.service_wrapper.server.Server")
    def test_loads_from_an_array_of_classes(self, mock_serve):
        service_wrapper.main(['cmd_name'], [mock.MagicMock])
        mock_serve.assert_called_with(
            bus_class=dbus.SystemBus,
            bus_name=constants.BUS_NAME,
            object_classes=[mock.MagicMock]
        )
