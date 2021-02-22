# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
#
# Copyright (c) 2018 Red Hat, Inc.
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

import json
import pprint
import unittest
import tempfile
import shutil
import six
import sys
import traceback


class SyspurposeTestBase(unittest.TestCase):

    def _mktmp(self):
        """
        A Utility function to create a temporary directory and ensure it is deleted at the end of
        the test
        :return: string path to a new temp directory
        """
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        return temp_dir

    def assertRaisesNothing(self, *args, **kwargs):
        """
        Assert that the first arg given, when called with the remaining args and kwargs
        does not raise any exception
        :return: Whatever the call to the method returns
        """
        method = args[0]

        try:
            if kwargs:
                return method(*args[1:], **kwargs)
            else:
                return method(*args[1:])
        except Exception as e:
            _, _, tb = sys.exc_info()
            arguments = ""
            if args[1:]:
                arguments += ",".join([str(x) for x in args[1:]])
            if kwargs:
                arguments += str(kwargs)
            err_msg = "Expected no exception from method call \"{method}({args})\"\n Got Exception: \"{msg}\"\nTraceback during target method call:\n"\
                .format(method=method.__name__, args=arguments, msg=str(e)) + "".join(traceback.format_tb(tb))
            self.fail(err_msg)

    # Taken from subman test Fixtures
    def assert_equal_dict(self, expected_dict, actual_dict):
        mismatches = []
        missing_keys = []
        extra = []

        for key in expected_dict:
            if key not in actual_dict:
                missing_keys.append(key)
                continue
            if expected_dict[key] != actual_dict[key]:
                mismatches.append((key, expected_dict[key], actual_dict[key]))

        for key in actual_dict:
            if key not in expected_dict:
                extra.append(key)

        message = ""
        if missing_keys or extra:
            message += "Keys in only one dict: \n"
            if missing_keys:
                for key in missing_keys:
                    message += "actual_dict:  %s\n" % key
            if extra:
                for key in extra:
                    message += "expected_dict: %s\n" % key
        if mismatches:
            message += "Unequal values: \n"
            for info in mismatches:
                message += "%s: %s != %s\n" % info

        # pprint the dicts
        message += "\n"
        message += "expected_dict:\n"
        message += pprint.pformat(expected_dict)
        message += "\n"
        message += "actual_dict:\n"
        message += pprint.pformat(actual_dict)

        if mismatches or missing_keys or extra:
            self.fail(message)


class Capture(object):
    class Tee(object):
        def __init__(self, stream, silent):
            self.buf = six.StringIO()
            self.stream = stream
            self.silent = silent

        def write(self, data):
            self.buf.write(data)
            if not self.silent:
                self.stream.write(data)

        def flush(self):
            pass

        def getvalue(self):
            return self.buf.getvalue()

        def isatty(self):
            return False

    def __init__(self, silent=False):
        self.silent = silent

    def __enter__(self):
        self.buffs = (self.Tee(sys.stdout, self.silent), self.Tee(sys.stderr, self.silent))
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout, sys.stderr = self.buffs
        return self

    @property
    def out(self):
        return self.buffs[0].getvalue()

    @property
    def err(self):
        return self.buffs[1].getvalue()

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.stdout
        sys.stderr = self.stderr


# utility functions from syspurpose.utils to help ensure data written to files is utf-8
def make_utf8(obj):
    """
    Transforms the provided string into unicode if it is not already
    :param obj: the string to decode
    :return: the unicode format of the string
    """
    if six.PY3:
        return obj
    elif obj is not None and isinstance(obj, str) and not isinstance(obj, unicode):
        obj = obj.decode('utf-8')
        return obj
    else:
        return obj


def write_to_file_utf8(file, data):
    """
    Writes out the provided data to the specified file, with user-friendly indentation,
    and in utf-8 encoding.
    :param file: The file to write to
    :param data: The data to be written
    :return:
    """
    file.write(make_utf8(json.dumps(data, indent=2, ensure_ascii=False)))
