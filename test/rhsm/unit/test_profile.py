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
from unittest import mock
from unittest.mock import patch

from cloud_what.providers import aws, azure, gcp

from rhsm.profile import (
    ModulesProfile,
    EnabledReposProfile,
    parse_rpm_string,
    _is_ostree_system,
    _get_immutable_packages,
)


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
        # Mock cloud provider
        cloud_provider_patcher = patch("rhsm.profile.provider")
        self.cloud_provider_mock = cloud_provider_patcher.start()
        self.cloud_provider_mock.get_cloud_provider = mock.Mock(return_value=None)
        self.addCleanup(cloud_provider_patcher.stop)

    def tearDown(self) -> None:
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

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


class TestParseRpmString(unittest.TestCase):
    """
    Test case for parse_rpm_string function
    """

    def test_parse_valid_rpm_string_with_epoch(self):
        """
        Test parsing a valid RPM string with epoch
        """
        rpm_string = "NetworkManager-cloud-setup-1:1.54.0-2.fc43.x86_64"
        result = parse_rpm_string(rpm_string)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "NetworkManager-cloud-setup")
        self.assertEqual(result["version"], "1.54.0")
        self.assertEqual(result["epoch"], 1)
        self.assertEqual(result["release"], "2.fc43")
        self.assertEqual(result["arch"], "x86_64")

    def test_parse_valid_rpm_string_without_epoch(self):
        """
        Test parsing a valid RPM string without epoch
        """
        rpm_string = "bash-completion-2.16-2.fc43.noarch"
        result = parse_rpm_string(rpm_string)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "bash-completion")
        self.assertEqual(result["version"], "2.16")
        self.assertEqual(result["epoch"], 0)
        self.assertEqual(result["release"], "2.fc43")
        self.assertEqual(result["arch"], "noarch")

    def test_parse_rpm_string_with_hyphens_in_name(self):
        """
        Test parsing RPM string where package name contains multiple hyphens
        """
        rpm_string = "amd-ucode-firmware-20241210-164.fc42.noarch"
        result = parse_rpm_string(rpm_string)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "amd-ucode-firmware")
        self.assertEqual(result["version"], "20241210")
        self.assertEqual(result["epoch"], 0)
        self.assertEqual(result["release"], "164.fc42")
        self.assertEqual(result["arch"], "noarch")

    def test_parse_rpm_string_with_leading_whitespace(self):
        """
        Test parsing RPM string with leading whitespace
        """
        rpm_string = "  bash-5.2.32-1.fc42.x86_64"
        result = parse_rpm_string(rpm_string)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "bash")
        self.assertEqual(result["version"], "5.2.32")
        self.assertEqual(result["epoch"], 0)
        self.assertEqual(result["release"], "1.fc42")
        self.assertEqual(result["arch"], "x86_64")

    def test_parse_invalid_rpm_string(self):
        """
        Test parsing an invalid RPM string returns None
        """
        rpm_string = "invalid-package-string"
        result = parse_rpm_string(rpm_string)
        self.assertIsNone(result)

    def test_parse_empty_string(self):
        """
        Test parsing an empty string returns None
        """
        rpm_string = ""
        result = parse_rpm_string(rpm_string)
        self.assertIsNone(result)


class TestOstreeSystemDetection(unittest.TestCase):
    """
    Test case for ostree system detection functions
    """

    @patch("rhsm.profile.ostree_available", False)
    def test_is_ostree_system_without_ostree_library(self):
        """
        Test detection when ostree library is not available
        """
        result = _is_ostree_system()
        self.assertFalse(result)

    @patch("rhsm.profile.ostree_available", True)
    @patch("rhsm.profile.OSTree", create=True)
    def test_is_ostree_system_with_booted_deployment(self, mock_ostree):
        """
        Test detection when there is a booted ostree deployment
        """
        mock_sysroot = mock.Mock()
        mock_sysroot.load = mock.Mock()
        mock_sysroot.get_booted_deployment = mock.Mock(return_value=mock.Mock())

        mock_ostree.Sysroot.new_default.return_value = mock_sysroot

        result = _is_ostree_system()
        self.assertTrue(result)
        mock_sysroot.load.assert_called_once_with(None)
        mock_sysroot.get_booted_deployment.assert_called_once()

    @patch("rhsm.profile.ostree_available", True)
    @patch("rhsm.profile.OSTree", create=True)
    def test_is_ostree_system_without_booted_deployment(self, mock_ostree):
        """
        Test detection when there is no booted ostree deployment
        """
        mock_sysroot = mock.Mock()
        mock_sysroot.load = mock.Mock()
        mock_sysroot.get_booted_deployment = mock.Mock(return_value=None)
        mock_ostree.Sysroot.new_default.return_value = mock_sysroot
        result = _is_ostree_system()
        self.assertFalse(result)

    @patch("rhsm.profile.ostree_available", True)
    @patch("rhsm.profile.OSTree", create=True)
    def test_is_ostree_system_with_ostree_api_exception(self, mock_ostree):
        """
        Test detection when OSTree API raises an exception
        """
        mock_ostree.Sysroot.new_default.side_effect = Exception("OSTree API error")

        result = _is_ostree_system()
        self.assertFalse(result)

    @patch("subprocess.run")
    @patch("rhsm.profile.json.loads")
    def test_get_immutable_packages(self, mock_json_loads, mock_subprocess_run):
        """
        Test getting immutable packages from ostree system
        """
        # Mock rpm-ostree status output
        mock_status = {"deployments": [{"checksum": "abc123def456"}]}

        # Mock rpm-ostree db list output
        mock_db_list_output = """ostree commit: abc123def456
bash-5.2.32-1.fc42.x86_64
systemd-257.3-1.fc42.x86_64
NetworkManager-1:1.54.0-2.fc43.x86_64"""

        mock_subprocess_run.side_effect = [
            mock.Mock(stdout='{"deployments": [{"checksum": "abc123def456"}]}', returncode=0),
            mock.Mock(stdout=mock_db_list_output, returncode=0),
        ]

        mock_json_loads.return_value = mock_status

        result = _get_immutable_packages()

        self.assertIsInstance(result, set)
        # Check that result contains tuples with (name, version, epoch, release)
        self.assertIn(("bash", "5.2.32", 0, "1.fc42"), result)
        self.assertIn(("systemd", "257.3", 0, "1.fc42"), result)
        self.assertIn(("NetworkManager", "1.54.0", 1, "2.fc43"), result)
        self.assertEqual(len(result), 3)

    @patch("subprocess.run")
    def test_get_immutable_packages_command_failure(self, mock_run):
        """
        Test handling of rpm-ostree command failure
        """
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "rpm-ostree")

        result = _get_immutable_packages()

        self.assertIsInstance(result, set)
        self.assertEqual(len(result), 0)
