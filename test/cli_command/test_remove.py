import os

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli


class TestRemoveCommand(TestCliProxyCommand):
    command_class = managercli.RemoveCommand

    def test_validate_serial(self):
        self.cc.main(["--serial", "12345"])
        self.cc._validate_options()

    def test_validate_serial_not_numbers(self):
        self.cc.main(["--serial", "this is not a number"])
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_serial_no_value(self):
        try:
            self.cc.main(["--serial"])
        except SystemExit as e:
            self.assertEqual(e.code, 2)

    def test_validate_access_to_remove_by_pool(self):
        self.cc.main(["--pool", "a2ee88488bbd32ed8edfa2"])
        self.cc.cp._capabilities = ["remove_by_pool_id"]
        self.cc._validate_options()

    def test_validate_no_access_to_remove_by_pool(self):
        self.cc.main(["--pool", "a2ee88488bbd32ed8edfa2"])
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, 69)
