import os
import sys

from ..test_managercli import TestCliCommand
from subscription_manager import managercli

from mock import patch, Mock


class TestImportCertCommand(TestCliCommand):
    command_class = managercli.ImportCertCommand

    def setUp(self):
        super(TestImportCertCommand, self).setUp()
        argv_patcher = patch.object(sys, 'argv', ['subscription-manager', 'import'])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)

    def test_certificates(self):
        self.cc.is_registered = Mock(return_value=False)
        self.cc.main(["--certificate", "one", "--certificate", "two"])
        self.cc._validate_options()

    def test_registered(self):
        self.cc.is_registered = Mock(return_value=True)
        self.cc.main(["--certificate", "one", "--certificate", "two"])
        with self.assertRaises(SystemExit) as e:
            self.cc._validate_options()
        self.assertEqual(os.EX_USAGE, e.exception.code)

    def test_no_certificates(self):
        try:
            self.cc.main([])
        except SystemExit as e:
            self.assertEqual(e.code, 2)

        try:
            self.cc._validate_options()
            self.fail("No exception raised")
        except Exception:
            pass
        except SystemExit as e:
            # there seems to be an optparse issue
            # here that depends on version, on f14
            # we get sysexit with return code 2  from main, on f15, we
            # get os.EX_USAGE from validate_options
            # i18n_optparse returns 2 on no args
            self.assertEqual(e.code, os.EX_USAGE)
