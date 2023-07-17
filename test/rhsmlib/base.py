#! /usr/bin/env python
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
from typing import Dict


import logging
import unittest
from unittest import mock

from test.fixture import SubManFixture

log = logging.getLogger(__name__)


class TestUtilsMixin:
    def assert_items_equals(self, a, b):
        """Assert that two lists contain the same items regardless of order."""
        if sorted(a) != sorted(b):
            self.fail("%s != %s" % (a, b))
        return True

    @staticmethod
    def write_temp_file(data):
        # create a temp file for use as a config file. This should get cleaned
        # up magically when it is closed so make sure to close it!
        fid = NamedTemporaryFile(mode="w+", suffix=".tmp")
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
        """
        Override this method to control what the injector returns
        """
        raise NotImplementedError("Subclasses should define injected objects")


class SubManDBusFixture(SubManFixture):
    patches: Dict[str, mock.Mock] = {}
    """Dictionary containing patch objects."""

    LOCALE: str = "C.UTF-8"

    @classmethod
    def tearDownClass(cls) -> None:
        # Stop patching
        for patch in cls.patches.values():
            try:
                patch.stop()
            except AttributeError as exc:
                raise RuntimeError(f"Object {patch} cannot be stopped.") from exc

        super().tearDownClass()
