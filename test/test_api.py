from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
from mock import patch, call, Mock

from subscription_manager import api
from subscription_manager.repolib import Repo

from .fixture import SubManFixture
from .stubs import StubUEP


class ApiVersionTest(SubManFixture):
    def test_version_is_available(self):
        from subscription_manager import version
        self.assertEqual(version.rpm_version, api.version)


class RepoApiTest(SubManFixture):
    def setUp(self):
        super(RepoApiTest, self).setUp()
        invoker_patcher = patch("subscription_manager.api.repos.RepoActionInvoker", autospec=True)
        self.invoker = invoker_patcher.start()
        self.addCleanup(invoker_patcher.stop)

        repo_file_patcher = patch("subscription_manager.api.repos.YumRepoFile", autospec=True)
        self.repo_file = repo_file_patcher.start()
        self.addCleanup(repo_file_patcher.stop)

        uep_patcher = patch("rhsm.connection.UEPConnection", new=StubUEP)
        self.stub_uep = uep_patcher.start()
        self.addCleanup(uep_patcher.stop)

        logging_patcher = patch("subscription_manager.api.logutil")
        logging_patcher.start()
        self.addCleanup(logging_patcher.stop)

    def test_disable_repo(self):
        repo_settings = {
            'enabled': '1',
        }
        self.invoker.return_value.get_repos.return_value = [
            Repo('hello', list(repo_settings.items())),
        ]
        self.repo_file.items.return_value = list(repo_settings.items())
        result = api.disable_yum_repositories('hello')

        self.repo_file.return_value.write.assert_called_with()
        self.assertEqual(1, result)

    def test_enable_repo(self):
        repo_settings = {
            'enabled': '0',
        }
        self.invoker.return_value.get_repos.return_value = [
            Repo('hello', list(repo_settings.items())),
        ]
        self.repo_file.items.return_value = list(repo_settings.items())
        result = api.enable_yum_repositories('hello')

        self.repo_file.return_value.write.assert_called_with()
        self.assertEqual(1, result)

    def test_enable_repo_wildcard(self):
        repo_settings = {
            'enabled': '0',
        }

        self.invoker.return_value.get_repos.return_value = [
            Repo('hello', list(repo_settings.copy().items())),
            Repo('helium', list(repo_settings.copy().items())),
        ]
        self.repo_file.items.return_value = list(repo_settings.copy().items())

        result = api.enable_yum_repositories('he*')
        self.repo_file.return_value.write.assert_called_with()
        self.assertEqual(2, result)

    def test_does_not_enable_nonmatching_repos(self):
        repo_settings = {
            'enabled': '0',
        }
        self.invoker.return_value.get_repos.return_value = [
            Repo('x', list(repo_settings.items())),
        ]
        self.repo_file.items.return_value = list(repo_settings.items())
        result = api.enable_yum_repositories('hello')

        self.assertEqual(0, len(self.repo_file.return_value.write.mock_calls))
        self.assertEqual(0, result)

    def test_update_overrides_cache(self):
        with patch('rhsm.connection.UEPConnection') as mock_uep:
            self.stub_cp_provider.consumer_auth_cp = mock_uep
            mock_uep.supports_resource = Mock(return_value=True)
            mock_uep.setContentOverrides = Mock()

            repo_settings = {
                'enabled': '0',
            }
            self.invoker.return_value.get_repos.return_value = [
                Repo('hello', list(repo_settings.items())),
            ]
            self.repo_file.items.return_value = list(repo_settings.items())

            self._inject_mock_valid_consumer("123")

            # The API methods try to bootstrap injection themselves so we want
            # to avoid that here.
            with patch('subscription_manager.api.injected') as injected:
                injected.return_value = True

                result = api.enable_yum_repositories('hello')

                expected_overrides = [{
                    'contentLabel': 'hello',
                    'name': 'enabled',
                    'value': '1',
                }]
                self.assertTrue(call("123", expected_overrides) in mock_uep.setContentOverrides.mock_calls)

                self.invoker.return_value.update.assert_called_with()
                self.assertEqual(1, result)
