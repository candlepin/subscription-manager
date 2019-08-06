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

from mock import MagicMock, patch

# Mock importing subscription_manager modules, because we do not want to print
# anything to log or exit the testing application in tests
import sys
sys.modules['subscription_manager'] = MagicMock()
sys.modules['subscription_manager.cli'] = MagicMock()

from syspurpose import cli, files
from .base import SyspurposeTestBase, Capture
import os


class SyspurposeCliTests(SyspurposeTestBase):

    def setUp(self):
        self.OLD_PATH = files.SyncedStore.PATH
        self.OLD_CACHE_PATH = files.SyncedStore.CACHE_PATH
        self.tmp_dir = self._mktmp()
        os.makedirs(self.tmp_dir + '/cache')
        files.SyncedStore.PATH = self.tmp_dir + '/syspurpose.json'
        with open(files.SyncedStore.PATH, "w") as fp:
            fp.write("{}")
        files.SyncedStore.CACHE_PATH = self.tmp_dir + '/cache/syspurpose.json'
        with open(files.SyncedStore.CACHE_PATH, "w") as fp:
            fp.write("{}")
        self.syspurposestore = files.SyncedStore(uep=None, consumer_uuid=None)

    def tearDown(self):
        files.SyncedStore.PATH = self.OLD_PATH
        files.SyncedStore.CACHE_PATH = self.OLD_CACHE_PATH

    def test_unset_command(self):
        """
        A smoke test to ensure nothing bizarre happens when we try to unset some attribute
        """
        args = MagicMock()
        args.prop_name = "foo"
        with Capture() as captured:
            cli.unset_command(args, self.syspurposestore)
            self.assertTrue('foo unset' in captured.out)

    def test_set_command(self):
        """
        A smoke test to ensure nothing bizarre happens when we try to set some attribute
        """
        args = MagicMock()
        args.prop_name = "foo"
        args.value = "bar"
        with Capture() as captured:
            cli.set_command(args, self.syspurposestore)
            self.assertTrue('foo set to "bar"' in captured.out)

    def test_add_command_one_value(self):
        """
        A smoke test to ensure nothing bizarre happens when we try to add some attribute
        """
        args = MagicMock()
        args.prop_name = "addons"
        args.values = ["ADDON1"]
        with Capture() as captured:
            cli.add_command(args, self.syspurposestore)
            self.assertTrue('Added ADDON1 to addons' in captured.out)

    def test_add_command_more_values(self):
        """
        A smoke test to ensure nothing bizarre happens when we try to add value to addons attribute
        """
        args = MagicMock()
        args.prop_name = "addons"
        args.values = ["ADDON1", "ADDON2"]
        with Capture() as captured:
            cli.add_command(args, self.syspurposestore)
            self.assertTrue('Added ADDON1 to addons' in captured.out)
            self.assertTrue('Added ADDON2 to addons' in captured.out)

    def test_remove_command(self):
        """
        A smoke test to ensure nothing bizarre happens when we try to remove one value from addons attribute
        """
        args = MagicMock()

        # Add value first
        args.prop_name = "addons"
        args.values = ["ADDON1"]
        cli.add_command(args, self.syspurposestore)

        # Now we can try to remove value
        with Capture() as captured:
            cli.remove_command(args, self.syspurposestore)
            self.assertTrue('Removed "ADDON1" from addons' in captured.out)

    def test_show_command(self):
        """
        A smoke test to ensure nothing bizarre happens when we try to show content fo syspurpose.json file
        """
        args = MagicMock()

        # Add value first
        with Capture() as captured:
            cli.show_contents(args, self.syspurposestore)
            self.assertTrue('{}' in captured.out)
