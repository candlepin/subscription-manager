#! /usr/bin/env python
from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from test.fixture import SubManFixture

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import dbus
import dbus.lowlevel
import dbus.bus
import dbus.mainloop.glib
import logging
import mock

import rhsmlib.dbus.base_object
from rhsmlib.dbus import constants
from subscription_manager.i18n import Locale

from test import subman_marker_dbus

# Set DBus mainloop early in test run (test import time!)
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
log = logging.getLogger(__name__)


class TestUtilsMixin(object):
    def assert_items_equals(self, a, b):
        """Assert that two lists contain the same items regardless of order."""
        if sorted(a) != sorted(b):
            self.fail("%s != %s" % (a, b))
        return True

    def write_temp_file(self, data):
        # create a temp file for use as a config file. This should get cleaned
        # up magically when it is closed so make sure to close it!
        fid = NamedTemporaryFile(mode='w+', suffix='.tmp')
        fid.write(data)
        fid.seek(0)
        return fid


class InjectionMockingTest(unittest.TestCase):
    def setUp(self):
        super(InjectionMockingTest, self).setUp()
        injection_patcher = mock.patch("rhsmlib.dbus.base_object.inj.require")
        self.mock_require = injection_patcher.start()
        self.addCleanup(injection_patcher.stop)
        self.mock_require.side_effect = self.injection_definitions

    def injection_definitions(self, *args, **kwargs):
        '''Override this method to control what the injector returns'''
        raise NotImplementedError("Subclasses should define injected objects")


@subman_marker_dbus
class DBusServerStubProvider(SubManFixture):
    """Special class used start a DBus server.

    All rhsmlib.objects.*.*DbusObject classes need a connection, object path
    and a bus name to be instantiated. The functions they expose over DBus API
    are converted to via decorators to special methods the dbus-python library
    can use, but we can use `__wrapped__` attribute of these methods to obtain
    original Python functions.

    This will allow us to test just our implementation, without full
    communication over DBus.
    """

    LOCALE: str = "C.UTF-8"
    """Locale that is passed to DBus functions."""

    dbus_class: type = NotImplemented
    """DBus RHSM API class, subclass of `BaseObject`."""

    dbus_class_kwargs: Dict[str, Any] = {}
    """Extra arguments to pass to the DBus RHSM API class."""

    obj: Optional[rhsmlib.dbus.base_object.BaseObject] = None
    """DBus class instance used for testing."""

    patches: Dict[str, mock.Mock] = {}
    """Dictionary containing patch objects."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.obj = cls.dbus_class(
            conn=None,
            object_path=cls.dbus_class.default_dbus_path,
            bus_name=dbus.service.BusName(constants.BUS_NAME, bus=dbus.SessionBus()),
            **cls.dbus_class_kwargs,
        )

        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        # Unload current DBus class
        cls.obj = None

        # Stop patching
        for patch in cls.patches.values():
            try:
                patch.stop()
            except AttributeError as exc:
                raise RuntimeError(f"Object {patch} cannot be stopped.") from exc

        super().tearDownClass()

    def tearDown(self) -> None:
        # Always reset the locale to default value.
        # Some tests (Attach, for example) are passing non-english language
        # strings to DBus methods, which are changing the global locale
        # settings. This teardown makes sure the language will always be reset.
        Locale.set(self.LOCALE)

        super().tearDown()
