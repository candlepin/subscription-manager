#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import os
import shutil
import tarfile
from datetime import datetime

import fixture
from test_managercli import TestCliCommand

from rhsm_debug import debug_commands
from rhsm_debug import cli
from rhsm.config import initConfig
from subscription_manager.cli import InvalidCLIOptionError


cfg = initConfig()


def path_join(first, second):
    if os.path.isabs(second):
        second = second[1:]
    return os.path.join(first, second)


class TestRhsmDebugCLI(fixture.SubManFixture):
    def test_init(self):
        cli_obj = cli.RhsmDebugCLI()
        # we populated cli_commands
        self.assertTrue(cli_obj.cli_commands)
        # no aliases
        self.assertFalse(cli_obj.cli_aliases)


class TestCompileCommand(TestCliCommand):

    command_class = debug_commands.SystemCommand

    # Runs the tar file creation.
    # It does not write the certs or log files because of
    # permissions. It will make those dirs in tar.
    def test_command_tar(self):
        try:
            self.cc._do_command = self._orig_do_command
            self.cc._make_code = self._make_code
            self.cc._get_assemble_dir = self._get_assemble_dir
            self.cc._copy_directory = self._copy_directory
            self.cc._makedir = self._makedir
            self.test_dir = os.getcwd()
            path = path_join(self.test_dir, "testing-dir")
            self._makedir(path)
            self.cc.main(["--destination", path])
        except SystemExit:
            self.fail("Exception Raised")

        try:
            tar_path = path_join(path, "rhsm-debug-system-%s.tar.gz" % self.time_code)
            tar_file = tarfile.open(tar_path, "r")
            self.assertTrue(tar_file.getmember(path_join(self.code, "consumer.json")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "compliance.json")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "entitlements.json")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "pools.json")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "version.json")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "subscriptions.json")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "/etc/rhsm")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "/var/log/rhsm")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "/var/lib/rhsm")) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, cfg.get('rhsm', 'productCertDir'))) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, cfg.get('rhsm', 'entitlementCertDir'))) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, cfg.get('rhsm', 'consumerCertDir'))) is not None)
            self.assertTrue(tar_file.getmember(path_join(self.code, "etc/pki/product-default")) is not None)
        finally:
            shutil.rmtree(path)

    # Runs the non-tar tree creation.
    # It does not write the certs or log files because of
    # permissions. It will make those dirs in tree.
    def test_command_tree(self):
        try:
            self.cc._do_command = self._orig_do_command
            self.cc._make_code = self._make_code
            self.cc._get_assemble_dir = self._get_assemble_dir
            self.cc._copy_directory = self._copy_directory
            self.cc._makedir = self._makedir
            self.test_dir = os.getcwd()
            path = path_join(self.test_dir, "testing-dir")
            self._makedir(path)
            self.cc.main(["--destination", path, "--no-archive"])
        except SystemExit:
            self.fail("Exception Raised")

        try:
            tree_path = path_join(path, self.code)
            self.assertTrue(os.path.exists(path_join(tree_path, "consumer.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "compliance.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "entitlements.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "pools.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "version.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "subscriptions.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "/etc/rhsm")))
            self.assertTrue(os.path.exists(path_join(tree_path, "/var/log/rhsm")))
            self.assertTrue(os.path.exists(path_join(tree_path, "/var/lib/rhsm")))
            self.assertTrue(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'productCertDir'))))
            self.assertTrue(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'entitlementCertDir'))))
            self.assertTrue(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'consumerCertDir'))))
            self.assertTrue(os.path.exists(path_join(tree_path, "/etc/pki/product-default")))
        finally:
            shutil.rmtree(path)

    # Runs the non-tar tree creation.
    # sos flag limits included data
    def test_command_sos(self):
        try:
            self.cc._do_command = self._orig_do_command
            self.cc._make_code = self._make_code
            self.cc._get_assemble_dir = self._get_assemble_dir
            self.cc._copy_directory = self._copy_directory
            self.cc._makedir = self._makedir
            self.test_dir = os.getcwd()
            path = path_join(self.test_dir, "testing-dir")
            self._makedir(path)
            self.cc.main(["--destination", path, "--no-archive", "--sos"])
        except SystemExit:
            self.fail("Exception Raised")

        try:
            tree_path = path_join(path, self.code)
            self.assertTrue(os.path.exists(path_join(tree_path, "consumer.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "compliance.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "entitlements.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "pools.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "version.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "subscriptions.json")))
            self.assertFalse(os.path.exists(path_join(tree_path, "/etc/rhsm")))
            self.assertFalse(os.path.exists(path_join(tree_path, "/var/log/rhsm")))
            self.assertFalse(os.path.exists(path_join(tree_path, "/var/lib/rhsm")))
            # if cert directories are default, these should not be included
            self.assertFalse(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'productCertDir'))))
            self.assertFalse(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'entitlementCertDir'))))
            self.assertFalse(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'consumerCertDir'))))
            self.assertFalse(os.path.exists(path_join(tree_path, "/etc/pki/product-default")))
        finally:
            shutil.rmtree(path)

    # Runs the non-tar tree creation.
    # no-subscriptions flag limits included data
    def test_command_no_subs(self):
        try:
            self.cc._do_command = self._orig_do_command
            self.cc._make_code = self._make_code
            self.cc._get_assemble_dir = self._get_assemble_dir
            self.cc._copy_directory = self._copy_directory
            self.cc._makedir = self._makedir
            self.test_dir = os.getcwd()
            path = path_join(self.test_dir, "testing-dir")
            self._makedir(path)
            self.cc.main(["--destination", path, "--no-archive", "--no-subscriptions"])
        except SystemExit:
            self.fail("Exception Raised")

        try:
            tree_path = path_join(path, self.code)
            self.assertTrue(os.path.exists(path_join(tree_path, "consumer.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "compliance.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "entitlements.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "pools.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "version.json")))
            self.assertFalse(os.path.exists(path_join(tree_path, "subscriptions.json")))
            self.assertTrue(os.path.exists(path_join(tree_path, "/etc/rhsm")))
            self.assertTrue(os.path.exists(path_join(tree_path, "/var/log/rhsm")))
            self.assertTrue(os.path.exists(path_join(tree_path, "/var/lib/rhsm")))
            # if cert directories are default, these should not be included
            self.assertTrue(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'productCertDir'))))
            self.assertTrue(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'entitlementCertDir'))))
            self.assertTrue(os.path.exists(path_join(tree_path, cfg.get('rhsm', 'consumerCertDir'))))
            self.assertTrue(os.path.exists(path_join(tree_path, "/etc/pki/product-default")))
        finally:
            shutil.rmtree(path)

    # Test to see that the filter on copy directory properly skips any -key.pem files
    def test_copy_private_key_filter(self):
        path1 = "./test-key-filter"
        path2 = "./result-dir"
        if not os.path.exists(path1):
            os.makedirs(path1)
        try:
            open(path_join(path1, "12346.pem"), 'a').close()
            open(path_join(path1, "7890.pem"), 'a').close()
            open(path_join(path1, "22222-key.pem"), 'a').close()
            self.cc._copy_cert_directory(path1, path2)

            self.assertTrue(os.path.exists(path_join(path2, path_join(path1, "12346.pem"))))
            self.assertTrue(os.path.exists(path_join(path2, path_join(path1, "7890.pem"))))
            self.assertFalse(os.path.exists(path_join(path2, path_join(path1, "22222-key.pem"))))
        finally:
            shutil.rmtree(path1)
            shutil.rmtree(path2)

    # by not creating the destination directory
    #  we expect the validation to fail
    def test_archive_to_non_exist_dir(self):
        self.test_dir = os.getcwd()
        path = path_join(self.test_dir, "testing-dir")
        try:
            self.cc.main(["--destination", path])
            self.cc._validate_options()
        except InvalidCLIOptionError, e:
            self.assertEquals(e.message, "The destination directory for the archive must already exist.")
        else:
            self.fail("No Exception Raised")

    # method to capture code
    def _make_code(self):
        self.time_code = datetime.now().strftime("%Y%m%d-%f")
        self.code = "rhsm-debug-system-%s" % self.time_code
        return self.time_code

    # directory we can write to while not root
    def _get_assemble_dir(self):
        self.assemble_path = path_join(self.test_dir, "assemble-dir/%s" % datetime.now().strftime("%Y%m%d-%f"))
        os.makedirs(path_join(self.assemble_path, "/etc/rhsm/ca/"))
        os.makedirs(path_join(self.assemble_path, "/etc/rhsm/pluginconf.d/"))
        os.makedirs(path_join(self.assemble_path, "/etc/rhsm/facts/"))
        os.makedirs(path_join(self.assemble_path, "/var/log/rhsm/"))
        os.makedirs(path_join(self.assemble_path, "/var/lib/rhsm/"))
        os.makedirs(path_join(self.assemble_path, cfg.get('rhsm', 'productCertDir')))
        os.makedirs(path_join(self.assemble_path, cfg.get('rhsm', 'entitlementCertDir')))
        os.makedirs(path_join(self.assemble_path, cfg.get('rhsm', 'consumerCertDir')))
        os.makedirs(path_join(self.assemble_path, "/etc/pki/product-default"))
        return self.assemble_path

    # write to my directory instead
    def _copy_directory(self, path, prefix, ignore_pats=[]):
        #print "_copy_directory: %s, %s" % (path, prefix)
        shutil.copytree(path_join(self.assemble_path, path), path_join(prefix, path))

    # tests run as non-root
    def _makedir(self, dest_dir_name):
        try:
            os.makedirs(dest_dir_name)
        except Exception:
            # already there, move on
            return
