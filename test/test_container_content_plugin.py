# Copyright (c) 2014 Red Hat, Inc.
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

import mock

from . import fixture
import tempfile
import shutil
import os.path

from os.path import exists, join

import imp
from subscription_manager.model import Content
from subscription_manager.plugin.container import \
    ContainerContentUpdateActionCommand, KeyPair, ContainerCertDir, \
    ContainerUpdateReport, RH_CDN_REGEX, RH_CDN_CA
from subscription_manager.plugins import PluginManager

DUMMY_CERT_LOCATION = "dummy/certs"

CA_NAME = os.path.basename(RH_CDN_CA)


class CdnRegexTests(fixture.SubManFixture):

    def test_cdn_match(self):
        self.assertTrue(RH_CDN_REGEX.match('cdn.redhat.com'))

    def test_stage_cdn_match(self):
        self.assertTrue(RH_CDN_REGEX.match('cdn.stage.redhat.com'))

    def test_anchors(self):
        self.assertFalse(RH_CDN_REGEX.match('something.cdn.redhat.com.org'))
        self.assertFalse(RH_CDN_REGEX.match('cdn.redhat.com.org'))
        self.assertFalse(RH_CDN_REGEX.match('something.cdn.redhat.com'))


class TestContainerContentUpdateActionCommand(fixture.SubManFixture):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subman-container-plugin-tests')
        self.src_certs_dir = join(self.temp_dir, "etc/pki/entitlement")
        os.makedirs(self.src_certs_dir)

        # This is where we'll setup for container certs:
        self.host_cert_dir = join(self.temp_dir,
                                  "etc/docker/certs.d/")
        os.makedirs(self.host_cert_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _create_content(self, label, cert):
        return Content("containerImage", label, label, cert=cert)

    def _mock_cert(self, base_filename):
        cert = mock.Mock()
        cert.path = join(self.temp_dir, DUMMY_CERT_LOCATION,
                         "%s.pem" % base_filename)
        cert.key_path.return_value = join(self.temp_dir, DUMMY_CERT_LOCATION,
                                          "%s-key.pem" % base_filename)
        return cert

    def test_unique_paths_with_dupes(self):
        cert1 = self._mock_cert('5001')
        cert2 = self._mock_cert('5002')
        cert3 = self._mock_cert('5003')

        content1 = self._create_content('content1', cert1)
        content2 = self._create_content('content2', cert1)
        content3 = self._create_content('content3', cert2)

        # This content is provided by two other certs:
        content1_dupe = self._create_content('content1', cert2)
        content1_dupe2 = self._create_content('content1', cert3)

        contents = [content1, content2, content3, content1_dupe,
                    content1_dupe2]
        cmd = ContainerContentUpdateActionCommand(None, ['cdn.example.org'],
                                                  self.host_cert_dir)
        cert_paths = cmd._get_unique_paths(contents)
        self.assertEqual(3, len(cert_paths))
        self.assertTrue(KeyPair(cert1.path, cert1.key_path()) in cert_paths)
        self.assertTrue(KeyPair(cert2.path, cert2.key_path()) in cert_paths)
        self.assertTrue(KeyPair(cert3.path, cert3.key_path()) in cert_paths)

    def test_multi_directory(self):
        host1 = 'hostname.example.org'
        host2 = 'hostname2.example.org'
        host3 = 'hostname3.example.org'

        self.assertFalse(exists(join(self.host_cert_dir, host1)))
        self.assertFalse(exists(join(self.host_cert_dir, host2)))
        self.assertFalse(exists(join(self.host_cert_dir, host3)))

        cmd = ContainerContentUpdateActionCommand(None, [host1, host2, host3],
                                                  self.host_cert_dir)
        cmd._find_content = mock.Mock(return_value=[])
        cmd.perform()

        self.assertTrue(exists(join(self.host_cert_dir, host1)))
        self.assertTrue(exists(join(self.host_cert_dir, host2)))
        self.assertTrue(exists(join(self.host_cert_dir, host3)))

    def test_post_install_main(self):
        plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'content_plugins'))
        fp, pathname, description = imp.find_module('container_content', [plugin_path])
        try:
            container_content = imp.load_module('container_content', fp, pathname, description)
        finally:
            fp.close()
        plugin_manager = PluginManager(search_path=plugin_path, plugin_conf_path=plugin_path)
        plugin_class = plugin_manager.get_plugins()['container_content.ContainerContentPlugin']
        with mock.patch.object(plugin_class, 'HOSTNAME_CERT_DIR', self.host_cert_dir):
            with mock.patch('subscription_manager.model.ent_cert.EntitlementDirEntitlementSource', autospec=True):
                with mock.patch('subscription_manager.plugins.PluginManager') as mock_plugin_manager:
                    mock_plugin_manager.side_effect = lambda: plugin_manager

                    registry_hostnames = [
                        'registry.access.redhat.com',
                        'cdn.redhat.com',
                        'access.redhat.com',
                        'registry.redhat.io',
                    ]

                    for hostname in registry_hostnames:
                        self.assertFalse(exists(join(self.host_cert_dir, hostname)), "%s cert dir should not exist" % hostname)

                    container_content.main()

                    for hostname in registry_hostnames:
                        self.assertTrue(exists(join(self.host_cert_dir, hostname)), "%s cert dir should exist" % hostname)


class TestKeyPair(fixture.SubManFixture):

    def test_expected_filenames(self):
        kp = KeyPair("/etc/pki/entitlement/9000.pem",
                     "/etc/pki/entitlement/9000-key.pem")
        self.assertEqual("9000.cert", kp.dest_cert_filename)
        self.assertEqual("9000.key", kp.dest_key_filename)

    def test_expected_filenames_weird_extensions(self):
        kp = KeyPair("/etc/pki/entitlement/9000.crt",
                     "/etc/pki/entitlement/9000-key.crt")
        self.assertEqual("9000.cert", kp.dest_cert_filename)
        self.assertEqual("9000.key", kp.dest_key_filename)

    def test_expected_filenames_weird_filenames(self):
        kp = KeyPair("/etc/pki/entitlement/9000.1.2014-a.pem",
                     "/etc/pki/entitlement/9000.1.2014-a-key.pem")
        self.assertEqual("9000.1.2014-a.cert", kp.dest_cert_filename)
        self.assertEqual("9000.1.2014-a.key", kp.dest_key_filename)

    def test_equality(self):
        kp = KeyPair("/etc/pki/entitlement/9000.pem",
                     "/etc/pki/entitlement/9000-key.pem")
        kp2 = KeyPair("/etc/pki/entitlement/9000.pem",
                      "/etc/pki/entitlement/9000-key.pem")
        self.assertEqual(kp, kp2)

    def test_inequality(self):
        kp = KeyPair("/etc/pki/entitlement/9000.pem",
                     "/etc/pki/entitlement/9000-key.pem")
        kp2 = KeyPair("/etc/pki/entitlement/9001.pem",
                      "/etc/pki/entitlement/9001-key.pem")
        self.assertNotEqual(kp, kp2)
        self.assertNotEqual(kp, "somestring")

    def test_mixmatched_base_filenames(self):
        kp = KeyPair("/etc/pki/entitlement/9000.1.2014-a.pem",
                     "/etc/pki/entitlement/9000.1.2014-a-key.pem")
        self.assertEqual("9000.1.2014-a.cert", kp.dest_cert_filename)
        self.assertEqual("9000.1.2014-a.key", kp.dest_key_filename)


class TestContainerCertDir(fixture.SubManFixture):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subman-container-plugin-tests')
        self.src_certs_dir = join(self.temp_dir, "etc/pki/entitlement")
        os.makedirs(self.src_certs_dir)

        # This is where we'll setup for container certs:
        container_dir = join(self.temp_dir,
                             "etc/docker/certs.d/")
        os.makedirs(container_dir)

        # Where we expect our certs to actually land:
        self.dest_dir = join(container_dir, 'cdn.redhat.com')
        self.report = ContainerUpdateReport()
        self.container_dir = ContainerCertDir(self.report, 'cdn.redhat.com',
                                              host_cert_dir=container_dir)
        self.container_dir._rh_cdn_ca_exists = mock.Mock(return_value=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _touch(self, dir_path, filename):
        """
        Create an empty file in the given directory with the given filename.
        """
        if not exists(dir_path):
            os.makedirs(dir_path)
        open(join(dir_path, filename), 'a').close()

    def test_first_install(self):
        cert1 = '1234.pem'
        key1 = '1234-key.pem'
        self._touch(self.src_certs_dir, cert1)
        self._touch(self.src_certs_dir, key1)
        kp = KeyPair(join(self.src_certs_dir, cert1),
                     join(self.src_certs_dir, key1))
        self.container_dir.sync([kp])
        self.assertTrue(exists(join(self.dest_dir, '1234.cert')))
        self.assertTrue(exists(join(self.dest_dir, '1234.key')))
        self.assertEqual(2, len(self.report.added))

    def test_old_certs_cleaned_out(self):
        cert1 = '1234.cert'
        key1 = '1234.key'
        ca = 'myca.crt'  # This file extension should be left alone:
        self._touch(self.dest_dir, cert1)
        self._touch(self.dest_dir, key1)
        self._touch(self.dest_dir, ca)
        self.assertTrue(exists(join(self.dest_dir, '1234.cert')))
        self.assertTrue(exists(join(self.dest_dir, '1234.key')))
        self.assertTrue(exists(join(self.dest_dir, ca)))
        self.container_dir.sync([])
        self.assertFalse(exists(join(self.dest_dir, '1234.cert')))
        self.assertFalse(exists(join(self.dest_dir, '1234.key')))
        self.assertTrue(exists(join(self.dest_dir, ca)))
        self.assertEqual(2, len(self.report.removed))

    def test_all_together_now(self):
        cert1 = '1234.pem'
        key1 = '1234-key.pem'
        cert2 = '12345.pem'
        key2 = '12345-key.pem'
        old_cert = '444.cert'
        old_key = '444.key'
        old_key2 = 'another.key'
        self._touch(self.src_certs_dir, cert1)
        self._touch(self.src_certs_dir, key1)
        self._touch(self.src_certs_dir, cert2)
        self._touch(self.src_certs_dir, key2)
        self._touch(self.dest_dir, old_cert)
        self._touch(self.dest_dir, old_key)
        self._touch(self.dest_dir, old_key2)
        kp = KeyPair(join(self.src_certs_dir, cert1),
                     join(self.src_certs_dir, key1))
        kp2 = KeyPair(join(self.src_certs_dir, cert2),
                      join(self.src_certs_dir, key2))
        self.container_dir.sync([kp, kp2])
        self.assertTrue(exists(join(self.dest_dir, '1234.cert')))
        self.assertTrue(exists(join(self.dest_dir, '1234.key')))
        self.assertTrue(exists(join(self.dest_dir, '12345.cert')))
        self.assertTrue(exists(join(self.dest_dir, '12345.key')))

        self.assertFalse(exists(join(self.dest_dir, '444.cert')))
        self.assertFalse(exists(join(self.dest_dir, '444.key')))
        self.assertEqual(4, len(self.report.added))
        self.assertEqual(3, len(self.report.removed))

    @mock.patch("os.symlink")
    def test_cdn_ca_symlink(self, mock_link):
        cert1 = '1234.pem'
        key1 = '1234-key.pem'
        self._touch(self.src_certs_dir, cert1)
        self._touch(self.src_certs_dir, key1)
        kp = KeyPair(join(self.src_certs_dir, cert1),
                     join(self.src_certs_dir, key1))
        self.container_dir.sync([kp])

        expected_symlink = join(self.dest_dir, "%s.crt" % os.path.splitext(CA_NAME)[0])
        mock_link.assert_called_once_with(RH_CDN_CA, expected_symlink)

    def test_cdn_ca_doesnt_exist_no_symlink(self):
        cert1 = '1234.pem'
        key1 = '1234-key.pem'
        self._touch(self.src_certs_dir, cert1)
        self._touch(self.src_certs_dir, key1)
        kp = KeyPair(join(self.src_certs_dir, cert1),
                     join(self.src_certs_dir, key1))
        # Mock that /etc/rhsm/ca/redhat-entitlement-authority.pem doesn't exist:
        self.container_dir._rh_cdn_ca_exists = mock.Mock(return_value=False)
        self.container_dir.sync([kp])

        expected_symlink = join(self.dest_dir, "%s.crt" % os.path.splitext(CA_NAME)[0])
        self.assertFalse(exists(expected_symlink))

    def test_cdn_ca_symlink_already_exists(self):
        cert1 = '1234.pem'
        key1 = '1234-key.pem'
        self._touch(self.src_certs_dir, cert1)
        self._touch(self.src_certs_dir, key1)
        kp = KeyPair(join(self.src_certs_dir, cert1),
                     join(self.src_certs_dir, key1))
        self.container_dir.sync([kp])

        expected_symlink = join(self.dest_dir, "%s.crt" % os.path.splitext(CA_NAME)[0])

        # Run it again, the symlink already exists:
        with mock.patch("os.symlink") as mock_link:
            with mock.patch("os.path.exists") as mock_exists:
                # Make the real os.path.exists call unless the module is asking
                # about the symlink which should already exist in this test
                def side_effects(path):
                    if path == expected_symlink:
                        return True
                    return os.path.exists(path)
                mock_exists.side_effects = side_effects
                self.container_dir.sync([kp])
                self.assertFalse(mock_link.called)
