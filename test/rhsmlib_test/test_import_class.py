from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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
import inspect

from rhsmlib import import_class


class TestImportClass(unittest.TestCase):

    def test_import_class(self):
        """
        Simple test of importing class. It seems that we cannot use mock,
        but it is necessary to use some real package with module containing class.
        This unit test was created due to rewriting import_class to use
        importlib and not deprecated imp module.
        """
        clazz = import_class("rhsmlib.file_monitor.FilesystemWatcher")
        self.assertTrue(inspect.isclass(clazz))

    # def test_import_new_class(self):
    #     clazz = new_import_class("rhsmlib.file_monitor.FilesystemWatcher")
    #     print(clazz)
