from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from subscription_manager.exceptions import ExceptionMapper
from rhsm.connection import RestlibException


class MyRuntimeErrorBase(RuntimeError):
    def __init__(self, message):
        RuntimeError.__init__(self, message)


class MyRuntimeError(MyRuntimeErrorBase):
    def __init__(self, message):
        MyRuntimeErrorBase.__init__(self, message)


class OldStyleClass:
    def __init__(self):
        pass


class TestExceptionMapper(unittest.TestCase):

    def test_single_mapped_exception(self):
        expected_message = "Single Exception Message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = (expected_message, mapper.format_default)

        err = RuntimeError("Testing")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_subclass_mapped_by_base_class(self):
        expected_message = "Single Exception Message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = (expected_message, mapper.format_default)

        err = MyRuntimeError("Testing base class")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_subclass_preferred_over_base_class(self):
        expected_message = "Subclass Exception Message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = ("RuntimeError message", mapper.format_default)
        mapper.message_map[MyRuntimeErrorBase] = ("MyRuntimeErrorBase message", mapper.format_default)
        mapper.message_map[MyRuntimeError] = (expected_message, mapper.format_default)

        err = MyRuntimeError("Logged Only")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_can_map_middle_sub_class(self):
        expected_message = "MyRuntimeErrorBase message"
        mapper = ExceptionMapper()
        mapper.message_map[RuntimeError] = ("RuntimeError message", mapper.format_default)
        mapper.message_map[MyRuntimeErrorBase] = (expected_message, mapper.format_default)
        mapper.message_map[MyRuntimeError] = ("MyRuntimeError message", mapper.format_default)

        err = MyRuntimeErrorBase("Logged Only")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_search_for_base_class_with_gaps(self):
        mapper = ExceptionMapper()
        expected_message = "RuntimeError message"

        mapper.message_map[RuntimeError] = (expected_message, mapper.format_default)
        err = MyRuntimeError("Logged Only")
        self.assertEqual(expected_message, mapper.get_message(err))

    def test_restlib_exception_uses_custom_message(self):
        expected_message = "Expected MESSAGE"
        mapper = ExceptionMapper()

        err = RestlibException(404, expected_message)
        self.assertEqual("HTTP error code 404: %s" % expected_message, mapper.get_message(err))

    def test_returns_none_when_no_mapped_exception_present(self):
        mapper = ExceptionMapper()
        self.assertEqual(None, mapper.get_message(RuntimeError()))

    def test_can_support_old_style_classes(self):
        expected_message = "Old style class"
        mapper = ExceptionMapper()
        mapper.message_map[OldStyleClass] = (expected_message, mapper.format_default)

        err = OldStyleClass()
        self.assertEqual(expected_message, mapper.get_message(err))
