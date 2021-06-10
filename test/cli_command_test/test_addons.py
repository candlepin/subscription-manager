# -*- coding: utf-8 -*-

import json
import sys
from contextlib import ExitStack

from ..test_managercli import TestCliCommand
from subscription_manager import syspurposelib
from subscription_manager import managercli

from ..fixture import Capture

from mock import patch


class TestAddonsCommand(TestCliCommand):
    command_class = managercli.AddonsCommand

    def _set_syspurpose(self, syspurpose):
        """
        Set the mocked out syspurpose to the given dictionary of values.
        Assumes it is called after syspurposelib.USER_SYSPURPOSE is mocked out.
        :param syspurpose: A dict of values to be set as the syspurpose
        :return: None
        """
        with open(syspurposelib.USER_SYSPURPOSE, 'w') as sp_file:
            json.dump(syspurpose, sp_file, ensure_ascii=True)

    def setUp(self):
        syspurpose_patch = patch('syspurpose.files.SyncedStore')
        sp_patch = syspurpose_patch.start()
        self.addCleanup(sp_patch.stop)
        super(TestAddonsCommand, self).setUp()
        argv_patcher = patch.object(sys, 'argv', ['subscription-manager', 'addons'])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)
        syspurposelib.USER_SYSPURPOSE = self.write_tempfile("{}").name

    def tearDown(self):
        super(TestAddonsCommand, self).tearDown()
        syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

    def test_view(self):
        self._test_no_exception([])

    def test_add(self):
        self._test_no_exception(['--add', 'test'])

    def test_add_and_remove(self):
        self._test_exception(['--add', 'test', '--remove', 'something_else'])

    def test_remove(self):
        self._test_no_exception(['--remove', 'test'])

    def test_unset(self):
        self._test_no_exception(['--unset'])

    def test_unset_and_add_and_remove(self):
        self._test_exception(['--add', 'test', '--remove', 'item', '--unset'])

    def test_add_valid_value(self):
        with patch.object(self.cc, '_get_valid_fields') as mock_get_valid_fields:
            mock_get_valid_fields.return_value = {'addons': ['ADDON1', 'ADDON3', 'ADDON2']}
            self.assertTrue(self.cc._is_provided_value_valid('ADDON1'))
            with Capture() as cap:
                self.assertEqual(self.cc._are_provided_values_valid(['ADDON1']), [])
            self.assertNotIn('Warning: Provided value', cap.out)

    def test_add_invalid_value(self):
        with patch.object(self.cc, '_get_valid_fields') as mock_get_valid_fields:
            mock_get_valid_fields.return_value = {'addons': ['ADDON1', 'ADDON3', 'ADDON2']}
            self.assertFalse(self.cc._is_provided_value_valid('test'))
            with Capture() as cap:
                self.assertEqual(self.cc._are_provided_values_valid(['test']), ['test'])
            self.assertIn('Warning: Provided value', cap.out)

    def test_no_valid_values(self):
        with ExitStack() as stack:
            mock_get_valid_fields = stack.enter_context(patch.object(self.cc, '_get_valid_fields'))
            cap = stack.enter_context(Capture())
            mock_get_valid_fields.return_value = {'addons': []}
            self.assertFalse(self.cc._is_provided_value_valid('test'))
            self.assertIn('Warning: This organization does not have', cap.out)
