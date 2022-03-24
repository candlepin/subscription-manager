# Copyright (c) 2011 - 2022 Red Hat, Inc.
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

import tempfile
import unittest
import mock
from mock import patch

from rhsm.profile import ModulesProfile, EnabledReposProfile


class TestModulesProfile(unittest.TestCase):
    """
    Class for testing ModulesProfile (reporting of modulemd in combined profile)
    """

    def setUp(self) -> None:
        # Mock dnf module
        dnf_patcher = patch("rhsm.profile.dnf")
        self.dnf_mock = dnf_patcher.start()
        self.addCleanup(dnf_patcher.stop)
        # Mock libdnf module
        libdnf_patcher = patch("rhsm.profile.libdnf")
        self.libdnf_mock = libdnf_patcher.start()
        self.addCleanup(libdnf_patcher.stop)

    def test_default_status(self) -> None:
        """
        Test the case, when module is not enabled nor disabled. The status of module
        should be default
        """
        base_mock = mock.Mock()
        base_mock._moduleContainer = mock.Mock()
        base_mock._moduleContainer.isEnabled = mock.Mock(return_value=False)
        base_mock._moduleContainer.isDisabled = mock.Mock(return_value=False)
        base_mock._moduleContainer.isModuleActive = mock.Mock(return_value=False)
        module_pkg_mock = mock.Mock()
        profile_mock = mock.Mock()
        profile_mock.getName = mock.Mock(return_value="mock_profile")
        module_pkg_mock.getProfiles = mock.Mock(return_value=[profile_mock])
        module_pkg_mock.getName = mock.Mock(return_value="mock_module")
        module_pkg_mock.getStream = mock.Mock(return_value="1.23")
        module_pkg_mock.getVersion = mock.Mock(return_value="123456789")
        module_pkg_mock.getContext = mock.Mock(return_value="abcdefgh")
        module_pkg_mock.getArch = mock.Mock(return_value="x86_64")
        self.all_module_list = [module_pkg_mock]
        base_mock._moduleContainer.getModulePackages = mock.Mock(return_value=self.all_module_list)
        self.dnf_mock.Base = mock.Mock(return_value=base_mock)

        modules_profile = ModulesProfile()

        self.assertEqual(len(modules_profile.content), 1)
        self.assertEqual(modules_profile.content[0]["status"], "default")
        self.assertEqual(modules_profile.content[0]["active"], False)

    def test_default_status_active(self) -> None:
        """
        Test the case, when module is not enabled nor disabled. The status of module
        should be default. Test the case, when the module can be active despite it
        is in default state.
        """
        base_mock = mock.Mock()
        base_mock._moduleContainer = mock.Mock()
        base_mock._moduleContainer.isEnabled = mock.Mock(return_value=False)
        base_mock._moduleContainer.isDisabled = mock.Mock(return_value=False)
        base_mock._moduleContainer.isModuleActive = mock.Mock(return_value=True)
        module_pkg_mock = mock.Mock()
        profile_mock = mock.Mock()
        profile_mock.getName = mock.Mock(return_value="mock_profile")
        module_pkg_mock.getProfiles = mock.Mock(return_value=[profile_mock])
        module_pkg_mock.getName = mock.Mock(return_value="mock_module")
        module_pkg_mock.getStream = mock.Mock(return_value="1.23")
        module_pkg_mock.getVersion = mock.Mock(return_value="123456789")
        module_pkg_mock.getContext = mock.Mock(return_value="abcdefgh")
        module_pkg_mock.getArch = mock.Mock(return_value="x86_64")
        self.all_module_list = [module_pkg_mock]
        base_mock._moduleContainer.getModulePackages = mock.Mock(return_value=self.all_module_list)
        self.dnf_mock.Base = mock.Mock(return_value=base_mock)

        modules_profile = ModulesProfile()

        self.assertEqual(len(modules_profile.content), 1)
        self.assertEqual(modules_profile.content[0]["status"], "default")
        self.assertEqual(modules_profile.content[0]["active"], True)

    def test_disabled_status(self) -> None:
        """
        Test the case, when module is disabled.
        """
        base_mock = mock.Mock()
        base_mock._moduleContainer = mock.Mock()
        base_mock._moduleContainer.isEnabled = mock.Mock(return_value=False)
        base_mock._moduleContainer.isDisabled = mock.Mock(return_value=True)
        base_mock._moduleContainer.isModuleActive = mock.Mock(return_value=False)
        module_pkg_mock = mock.Mock()
        profile_mock = mock.Mock()
        profile_mock.getName = mock.Mock(return_value="mock_profile")
        module_pkg_mock.getProfiles = mock.Mock(return_value=[profile_mock])
        module_pkg_mock.getName = mock.Mock(return_value="mock_module")
        module_pkg_mock.getStream = mock.Mock(return_value="1.23")
        module_pkg_mock.getVersion = mock.Mock(return_value="123456789")
        module_pkg_mock.getContext = mock.Mock(return_value="abcdefgh")
        module_pkg_mock.getArch = mock.Mock(return_value="x86_64")
        self.all_module_list = [module_pkg_mock]
        base_mock._moduleContainer.getModulePackages = mock.Mock(return_value=self.all_module_list)
        self.dnf_mock.Base = mock.Mock(return_value=base_mock)

        modules_profile = ModulesProfile()

        self.assertEqual(len(modules_profile.content), 1)
        self.assertEqual(modules_profile.content[0]["status"], "disabled")
        self.assertEqual(modules_profile.content[0]["active"], False)

    def test_enabled_status(self) -> None:
        """
        Test the case, when module is enabled.
        """
        base_mock = mock.Mock()
        base_mock._moduleContainer = mock.Mock()
        base_mock._moduleContainer.isEnabled = mock.Mock(return_value=True)
        base_mock._moduleContainer.isDisabled = mock.Mock(return_value=False)
        base_mock._moduleContainer.isModuleActive = mock.Mock(return_value=True)
        module_pkg_mock = mock.Mock()
        profile_mock1 = mock.Mock()
        profile_mock1.getName = mock.Mock(return_value="mock_profile1")
        profile_mock2 = mock.Mock()
        profile_mock2.getName = mock.Mock(return_value="mock_profile2")
        module_pkg_mock.getProfiles = mock.Mock(return_value=[profile_mock1, profile_mock2])
        base_mock._moduleContainer.getInstalledProfiles = mock.Mock(return_value=("mock_profile1",))
        module_pkg_mock.getName = mock.Mock(return_value="mock_module")
        module_pkg_mock.getStream = mock.Mock(return_value="1.23")
        module_pkg_mock.getVersion = mock.Mock(return_value="123456789")
        module_pkg_mock.getContext = mock.Mock(return_value="abcdefgh")
        module_pkg_mock.getArch = mock.Mock(return_value="x86_64")
        self.all_module_list = [module_pkg_mock]
        base_mock._moduleContainer.getModulePackages = mock.Mock(return_value=self.all_module_list)
        self.dnf_mock.Base = mock.Mock(return_value=base_mock)

        modules_profile = ModulesProfile()

        self.assertEqual(len(modules_profile.content), 1)
        self.assertEqual(modules_profile.content[0]["status"], "enabled")
        self.assertEqual(modules_profile.content[0]["active"], True)


REPO_FILE_CONTENT = """
[slick-catlike-tools-1-rpms]
name = Slick Catlike Tools
baseurl = http://cdn.foo.com/content/dist/cats/1.0/$basearch/os
enabled = 0
gpgcheck = 1
gpgkey = file://
sslverify = 1
sslcacert = /etc/rhsm/ca/redhat-uep.pem
sslclientkey = /etc/pki/entitlement/1234567890-key.pem
sslclientcert = /etc/pki/entitlement/1234567890.pem
metadata_expire = 86400
enabled_metadata = 0

[fluffy-snake-tools-1-rpms]
name = Red Hat JBoss Core Services Text-Only Advisories
baseurl = http://cdn.foo.com/content/dist/snakes/1.0/$basearch/os
enabled = 1
gpgcheck = 1
gpgkey = file://
sslverify = 1
sslcacert = /etc/rhsm/ca/redhat-uep.pem
sslclientkey = /etc/pki/entitlement/1234567890-key.pem
sslclientcert = /etc/pki/entitlement/1234567890.pem
metadata_expire = 86400
enabled_metadata = 0
"""


class TestEnabledReposProfile(unittest.TestCase):
    """
    Test case of EnabledReposProfile class
    """

    def setUp(self) -> None:
        # Mock dnf module
        dnf_patcher = patch("rhsm.profile.dnf")
        self.dnf_mock = dnf_patcher.start()
        mock_db = mock.Mock()
        mock_db.conf = mock.Mock()
        mock_db.conf.substitutions = {"releasever": "1", "basearch": "x86_64"}
        self.dnf_mock.dnf.Base = mock.Mock(return_value=mock_db)
        self.addCleanup(dnf_patcher.stop)

    def test_enabled_repos(self):
        """
        Test the case, when there is one enabled repository
        """
        with tempfile.NamedTemporaryFile() as tmp_repo_file:
            tmp_repo_file.write(bytes(REPO_FILE_CONTENT, encoding="utf-8"))
            tmp_repo_file.flush()
            enabled_repos = EnabledReposProfile(tmp_repo_file.name)
            repo_list = enabled_repos.collect()
            self.assertEqual(len(repo_list), 1)
            self.assertEqual(repo_list[0]["repositoryid"], "fluffy-snake-tools-1-rpms")
            self.assertEqual(
                repo_list[0]["baseurl"], ["http://cdn.foo.com/content/dist/snakes/1.0/x86_64/os"]
            )
