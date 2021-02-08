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

# A group of tests for the miscellaneous utilities in the utils module of syspurpose

from .base import SyspurposeTestBase
import io
import os
import errno
import json
import mock

from syspurpose import utils


class UtilsTests(SyspurposeTestBase):

    def tearDown(self):
        utils.HOST_CONFIG_DIR = "/etc/rhsm-host/"

    def test_create_dir(self):
        """
        Verify that the create_dir utility method creates directories as we expect.
        :return:
        """
        temp_dir = self._mktmp()

        # A directory that does not exist yet
        new_dir = os.path.join(temp_dir, "new_dir")
        res = self.assertRaisesNothing(utils.create_dir, new_dir)
        self.assertTrue(os.path.exists(new_dir))
        # There was a change, so the result should be True
        self.assertTrue(res)

        # Create another directory
        existing_dir = os.path.join(temp_dir, "existing")
        os.mkdir(existing_dir, 0o644)
        res = self.assertRaisesNothing(utils.create_dir, existing_dir)
        # Should have been no change, so the result should be false
        self.assertFalse(res)

        # Create one more directory that does not have the right permissions
        bad_perm_dir = os.path.join(temp_dir, "bad_perm_dir")
        os.mkdir(bad_perm_dir, 0o400)

        impossible_sub_dir = os.path.join(bad_perm_dir, "any_sub_dir")

        self.assertRaisesNothing(utils.create_dir, impossible_sub_dir)
        self.assertFalse(os.path.exists(impossible_sub_dir))

    def test_create_file(self):
        temp_dir = self._mktmp()
        to_create = os.path.join(temp_dir, "my_cool_file.json")

        test_data = {"arbitrary_key": "arbitrary_value"}

        res = self.assertRaisesNothing(utils.create_file, to_create, test_data)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(to_create))

        with io.open(to_create, 'r', encoding='utf-8') as fp:
            actual_contents = json.load(fp)

        self.assertDictEqual(actual_contents, test_data)

        to_create = os.path.join(temp_dir, "my_super_chill_file.json")

        # And now when the file appears to exist
        with mock.patch('syspurpose.utils.io.open') as mock_open:
            error_to_raise = OSError()
            error_to_raise.errno = errno.EEXIST
            mock_open.side_effect = error_to_raise

            res = self.assertRaisesNothing(utils.create_file, to_create, test_data)
            self.assertFalse(res)

        to_create = os.path.join(temp_dir, "my_other_cool_file.json")

        # And now with an unexpected OSError
        with mock.patch('syspurpose.utils.io.open') as mock_open:
            error_to_raise = OSError()
            error_to_raise.errno = errno.E2BIG  # Anything aside from the ones expected
            mock_open.side_effect = error_to_raise

            self.assertRaises(OSError, utils.create_file, to_create, test_data)
            self.assertFalse(os.path.exists(to_create))
