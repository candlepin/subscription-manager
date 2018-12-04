from .fixture import SubManFixture, open_mock
import mock
from subscription_manager import syspurposelib
from subscription_manager.syspurposelib import SyspurposeSyncActionCommand, \
    SyspurposeSyncActionReport
import json


class SyspurposeLibTests(SubManFixture):
    """
    Tests various functions of the syspurposelib module.
    """

    def setUp(self):
        super(SyspurposeLibTests, self).setUp()

        patch1 = mock.patch('subscription_manager.syspurposelib.json', wraps=json)
        self.mock_json = patch1.start()
        self.addCleanup(patch1.stop)

        patch2 = mock.patch.object(syspurposelib, 'USER_SYSPURPOSE', new="/test/value")
        self.mock_sp_path = patch2.start()
        self.addCleanup(patch2.stop)

    def test_write_syspurpose(self):
        """
        Test that shows that the write_syspurpose method uses the SyspurposeStore when possible.
        :return:
        """
        test_values = {"role": "Test Role",
                       "addons": ["Some addon"],
                       "service_level_agreement": "Premium",
                       "usage": "Dev",
                       }

        # First mock out the SyspurposeStore
        with mock.patch.object(syspurposelib, 'SyncedStore') as sp_store:
            result = syspurposelib.write_syspurpose(test_values)

            sp_store.assert_called_with(None)
            sp_store.return_value.update_local.assert_called_with(test_values)

            self.assertEqual(result, True)

    def test_write_syspurpose_with_no_syspurpose_store(self):
        """
        Test that shows the backup method of writing to the syspurpose.json file works.
        :return:
        """
        test_values = {"role": "Test Role",
                       "addons": ["Some addon"],
                       "service_level_agreement": "Premium",
                       "usage": "Dev",
                       }

        with mock.patch.object(syspurposelib, 'SyncedStore', new=None):
            with open_mock() as mock_open:
                result = syspurposelib.write_syspurpose(test_values)
                self.mock_json.dump.assert_called_with(test_values, mock_open, ensure_ascii=True,
                                                       indent=2)
                self.assertEqual(result, True)
                self.assert_equal_dict(json.loads(mock_open.content_out()), test_values)

    def test_write_syspurpose_with_no_syspurpose_store_and_os_error(self):
        """
        Test that shows how the write_syspurpose method works with an error opening the file
        :return:
        """
        test_values = {"role": "Test Role",
                       "addons": ["Some addon"],
                       "service_level_agreement": "Premium",
                       "usage": "Dev",
                       }

        self.mock_json.dump.side_effect = OSError

        with mock.patch.object(syspurposelib, 'SyncedStore', new=None):
            with open_mock() as mock_open:
                result = syspurposelib.write_syspurpose(test_values)
                self.mock_json.dump.assert_called_with(test_values, mock_open, ensure_ascii=True,
                                                       indent=2)
                self.assertEqual(result, False)

                # We expect the file not to have been modified.
                self.assertEqual(mock_open.content_out(), "")


class SyspurposeSyncActionCommandTests(SubManFixture):

    def setUp(self):
        super(SyspurposeSyncActionCommandTests, self).setUp()

        self.command = SyspurposeSyncActionCommand()
        # Some mock data to use in tests
        self.remote_sp = {"role": "The best role",
                          "addOns": ["Super shiny Addon 1"],
                          "serviceLevel": "Topmost",
                          "usage": "Deviousness",
                          }
        self.base = {"role": self.remote_sp["role"],
                     "addons": self.remote_sp["addOns"],
                     "service_level_agreement": self.remote_sp["serviceLevel"],
                     "usage": self.remote_sp["usage"],
                     }
        self.local_sp = {"role": "Some Other Role",
                         "addons": self.remote_sp["addOns"],
                         "service_level_agreement": self.remote_sp["serviceLevel"],
                         "usage": self.remote_sp["usage"],
                         }

    def test_perform(self):
        """
        Super simple test to show that the perform method is running sync.
        :return:
        """
        with mock.patch('subscription_manager.syspurposelib.SyncedStore') as store:
            result = self.command.perform()
            store.return_value.sync.assert_called_once()
            self.assertTrue(isinstance(result, SyspurposeSyncActionReport))
