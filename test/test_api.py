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
from mock import patch, call

from subscription_manager import api
from subscription_manager.repolib import Repo

from test.fixture import SubManFixture
from test.stubs import StubUEP


class ApiVersionTest(SubManFixture):
    def test_version_is_available(self):
        from subscription_manager import version
        self.assertEquals(version.rpm_version, api.version)


@patch('subscription_manager.logutil.init_logger')
class RepoApiTest(SubManFixture):
    def setUp(self):
        super(RepoApiTest, self).setUp()
        self.invoker_patcher = patch("subscription_manager.api.repos.RepoActionInvoker", autospec=True)
        self.invoker = self.invoker_patcher.start().return_value

        self.repo_file_patcher = patch("subscription_manager.api.repos.RepoFile", autospec=True)
        self.repo_file = self.repo_file_patcher.start().return_value

    def tearDown(self):
        super(RepoApiTest, self).tearDown()
        self.invoker_patcher.stop()
        self.repo_file_patcher.stop()

    def test_disable_repo(self, mock_init_logger):
        repo_settings = {
            'enabled': '1',
        }
        self.invoker.get_repos.return_value = [
            Repo('hello', repo_settings.items()),
        ]
        self.repo_file.items.return_value = repo_settings.items()
        result = api.disable_yum_repositories('hello')

        self.assertTrue(call.write() in self.repo_file.mock_calls)
        self.assertEquals(1, result)

    def test_enable_repo(self, mock_init_logger):
        repo_settings = {
            'enabled': '0',
        }
        self.invoker.get_repos.return_value = [
            Repo('hello', repo_settings.items()),
        ]
        self.repo_file.items.return_value = repo_settings.items()
        result = api.enable_yum_repositories('hello')

        self.assertTrue(call.write() in self.repo_file.mock_calls)
        self.assertEquals(1, result)

    def test_enable_repo_wildcard(self, mock_init_logger):
        repo_settings = {
            'enabled': '0',
        }

        self.invoker.get_repos.return_value = [
            Repo('hello', repo_settings.copy().items()),
            Repo('helium', repo_settings.copy().items()),
        ]
        self.repo_file.items.return_value = repo_settings.copy().items()

        result = api.enable_yum_repositories('he*')

        self.assertTrue(call.write() in self.repo_file.mock_calls)
        self.assertEquals(2, result)

    def test_does_not_enable_nonmatching_repos(self, mock_init_logger):
        repo_settings = {
            'enabled': '0',
        }
        self.invoker.get_repos.return_value = [
            Repo('x', repo_settings.items()),
        ]
        self.repo_file.items.return_value = repo_settings.items()
        result = api.enable_yum_repositories('hello')

        self.assertFalse(call.write() in self.repo_file.mock_calls)
        self.assertEquals(0, result)

    @patch.object(StubUEP, 'supports_resource')
    @patch.object(StubUEP, 'setContentOverrides', create=True)
    def test_update_overrides_cache(self, mock_set, mock_supports, mock_init_logger):
        mock_supports.return_value = True

        repo_settings = {
            'enabled': '0',
        }
        self.invoker.get_repos.return_value = [
            Repo('hello', repo_settings.items()),
        ]
        self.repo_file.items.return_value = repo_settings.items()

        @api.request_injection
        def munge_injection():
            self._inject_mock_valid_consumer("123")
            return api.enable_yum_repositories('hello')

        result = munge_injection()

        expected_overrides = [{
            'contentLabel': 'hello',
            'name': 'enabled',
            'value': '1',
        }]
        self.assertTrue(call("123", expected_overrides) in mock_set.mock_calls)
        self.assertTrue(call.update() in self.invoker.mock_calls)
        self.assertEquals(1, result)
