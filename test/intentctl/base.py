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

import unittest
import tempfile
import shutil
import sys
import traceback


class IntentCtlTestBase(unittest.TestCase):

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
        err_msg = None

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

        if err_msg:
            self.fail(err_msg)
