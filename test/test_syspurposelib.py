from .fixture import SubManFixture, open_mock
import mock
import subscription_manager.injection as inj
from subscription_manager import syspurposelib
from subscription_manager.syspurposelib import SyspurposeSyncActionCommand, \
    SyspurposeSyncActionReport, ROLE, ADDONS, SERVICE_LEVEL, USAGE
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
        with mock.patch.object(syspurposelib, 'SyspurposeStore') as sp_store:
            result = syspurposelib.write_syspurpose(test_values)

            sp_store.assert_called_with(syspurposelib.USER_SYSPURPOSE)
            self.assert_equal_dict(sp_store.return_value.contents, test_values)

            # The current syspurposelib code assumes that the SyspurposeStore.write method
            # actually writes the values to the correct file.
            sp_store.return_value.write.assert_called_once()

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

        with mock.patch.object(syspurposelib, 'SyspurposeStore', new=None):
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

        with mock.patch.object(syspurposelib, 'SyspurposeStore', new=None):
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
        with mock.patch.object(self.command, 'sync') as sync_mock:
            result = self.command.perform()
            sync_mock.assert_called_once()
            self.assertTrue(isinstance(result, SyspurposeSyncActionReport))

    @mock.patch('subscription_manager.syspurposelib.write_syspurpose')
    @mock.patch('subscription_manager.syspurposelib.three_way_merge')
    @mock.patch('subscription_manager.syspurposelib.SyspurposeCache')
    @mock.patch('subscription_manager.syspurposelib.read_syspurpose')
    def test_sync(self, mock_read_sp, mock_cache, mock_merge, mock_write):
        """
        Ensure that sync updates the cache with the result of a three-way-merge with the values
        from the server, the values from the local file and the cache as the base.
        :return:
        """
        self._inject_mock_valid_consumer()

        # We expect that the remote keys have been mapped to the names used locally
        # e.g. addOns -> addons.
        #      serviceLevel -> service_level_agreement
        translated_remote = self.base

        # We want the cache instance not the class from which it is created
        mock_cache = mock_cache.return_value
        mock_cache.read_cache_only.return_value = self.base

        self.stub_cp_provider.consumer_auth_cp._capabilities.append('syspurpose')
        # We shouldn't expect that there are other values than those that are for syspurpose
        # although the real return value would include many more attributes
        self.stub_cp_provider.consumer_auth_cp.registered_consumer_info = self.remote_sp
        mock_read_sp.return_value = self.local_sp

        # To illustrate the effect of a three way merge in this case, only local changed the role.
        expected = {
            "role": self.local_sp["role"],
            "addons": self.remote_sp["addOns"],
            "service_level_agreement": self.remote_sp["serviceLevel"],
            "usage": self.remote_sp["usage"],
        }

        mock_merge.return_value = expected
        with mock.patch.object(self.stub_cp_provider.consumer_auth_cp, 'updateConsumer') as update:

            result = self.command.sync()

            mock_cache.read_cache_only.assert_called_once()
            mock_cache.write_cache.assert_called_once()

            mock_merge.assert_called_once_with(local=self.local_sp,
                                           base=self.base,
                                           remote=translated_remote,
                                           on_change=self.command.report.record_change)

            # The return value of sync should be the return value of the three_way_merge
            self.assert_equal_dict(result, mock_merge.return_value)

            # The value of the syspurpose attribute is written to the cache on write_cache.
            # So if these two are the same then the cache will have been updated with the new result.
            self.assert_equal_dict(mock_cache.syspurpose, mock_merge.return_value)

            mock_write.assert_called_once_with(mock_merge.return_value)
            ident = inj.require(inj.IDENTITY)
            update.assert_called_once_with(ident.uuid, role=result[ROLE],
                                           addons=result[ADDONS],
                                           service_level=result[SERVICE_LEVEL],
                                           usage=result[USAGE])

    @mock.patch('subscription_manager.syspurposelib.write_syspurpose')
    @mock.patch('subscription_manager.syspurposelib.three_way_merge')
    @mock.patch('subscription_manager.syspurposelib.SyspurposeCache')
    @mock.patch('subscription_manager.syspurposelib.read_syspurpose')
    def test_sync_missing_capability(self, mock_read_sp, mock_cache, mock_merge, mock_write):
        """
        Show that nothing is done if the server does not support the 'syspurpose' capability.
        Everything else that would otherwise need to be in place is in place. We are asserting
        that nothing that would otherwise have been done such as updating the cache, is done.
        :return:
        """

        # We want the cache instance not the class from which it is created
        mock_cache = mock_cache.return_value
        mock_cache.read_cache_only.return_value = self.base
        # We shouldn't expect that there are other values than those that are for syspurpose
        # although the real return value would include many more attributes
        self.stub_cp_provider.consumer_auth_cp.registered_consumer_info = self.remote_sp

        mock_read_sp.return_value = self.local_sp

        merged = {
            "role": self.local_sp["role"],
            "addons": self.remote_sp["addOns"],
            "service_level_agreement": self.remote_sp["serviceLevel"],
            "usage": self.remote_sp["usage"],
        }

        mock_merge.return_value = merged

        with mock.patch.object(self.stub_cp_provider.consumer_auth_cp, 'updateConsumer') as update:
            result = self.command.sync()

            mock_cache.read_cache_only.assert_not_called()
            mock_cache.write_cache.assert_not_called()

            mock_merge.assert_not_called()
            mock_write.assert_not_called()
            self.assertEqual(result, self.local_sp)

            update.assert_not_called()

    @mock.patch('subscription_manager.syspurposelib.write_syspurpose')
    @mock.patch('subscription_manager.syspurposelib.three_way_merge')
    @mock.patch('subscription_manager.syspurposelib.SyspurposeCache')
    @mock.patch('subscription_manager.syspurposelib.read_syspurpose')
    def test_sync_no_syspurpose_file(self, mock_read_sp, mock_cache, mock_merge, mock_write):
        """
        Ensure that sync updates the cache with the result of a three-way-merge with the values
        from the server, the values from the local file and the cache as the base.
        :return:
        """
        self._inject_mock_valid_consumer()

        # We want the cache instance not the class from which it is created
        mock_cache = mock_cache.return_value
        mock_cache.read_cache_only.return_value = self.base

        self.stub_cp_provider.consumer_auth_cp._capabilities.append('syspurpose')
        # We shouldn't expect that there are other values than those that are for syspurpose
        # although the real return value would include many more attributes
        self.stub_cp_provider.consumer_auth_cp.registered_consumer_info = self.remote_sp

        mock_read_sp.side_effect = OSError

        # To illustrate the effect of a three way merge in this case, only local changed the role.
        expected = {
            "role": self.remote_sp["role"],
            "addons": self.remote_sp["addOns"],
            "service_level_agreement": self.remote_sp["serviceLevel"],
            "usage": self.remote_sp["usage"],
        }

        mock_merge.return_value = expected

        with mock.patch.object(self.stub_cp_provider.consumer_auth_cp, 'updateConsumer') as update:
            result = self.command.sync()

            mock_cache.read_cache_only.assert_not_called()
            mock_cache.write_cache.assert_called_once()

            mock_merge.assert_not_called()

            # The return value of sync should be the return value of the three_way_merge
            self.assert_equal_dict(result, expected)

            # The value of the syspurpose attribute is written to the cache on write_cache.
            # So if these two are the same then the cache will have been updated with the new result.
            self.assert_equal_dict(mock_cache.syspurpose, expected)

            mock_write.assert_called_once_with(expected)
            ident = inj.require(inj.IDENTITY)
            update.assert_called_once_with(ident.uuid, role=result[ROLE],
                                           addons=result[ADDONS],
                                           service_level=result[SERVICE_LEVEL],
                                           usage=result[USAGE])
