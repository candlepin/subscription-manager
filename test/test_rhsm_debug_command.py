from __future__ import print_function, division, absolute_import

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
import logging
import shutil
import tarfile
import tempfile
from datetime import datetime

from . import fixture
from .test_managercli import TestCliCommand
import six

from rhsm_debug import debug_commands
from rhsm_debug import cli
from rhsm.config import initConfig
from subscription_manager.cli import InvalidCLIOptionError


cfg = initConfig()

log = logging.getLogger(__name__)


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

    def setUp(self):
        super(TestCompileCommand, self).setUp()

        # FIXME: likely all this should be mock/patched
        self.cc._do_command = self._orig_do_command
        self._orig_make_code = self.cc._make_code
        self.cc._make_code = self._make_code
        self._orig_copy_directory = self.cc._copy_directory
        self.cc._copy_directory = self._copy_directory
        self.cc._makedir = self._makedir

        self.test_dir = self._get_test_dir()

        self.path = self._create_test_path(self.test_dir)
        self.assemble_top_dir = os.path.join(self.test_dir, "assemble-dir")
        self.assemble_path = self._create_assemble_dir(self.assemble_top_dir)

        # monkeypatch cli commands assemble path
        self.cc.assemble_path = self.assemble_path

        self.expected_paths = ["consumer.json", "compliance.json", "entitlements.json",
                               "pools.json", "version.json",
                               "/etc/rhsm", "/var/log/rhsm", "/var/lib/rhsm",
                               # we use a test specific config, with default values
                               "/etc/pki/product",
                               "/etc/pki/entitlement", "/etc/pki/consumer",
                               "/etc/pki/product-default"]

    def _rmtree_error_callback(self, function, path, excinfo):
        """Ignore errors in rmtree, but log them."""
        log.debug("rmtree on path %s", path)
        log.exception(excinfo)

    def _rmtree(self, path):
        log.debug("rmtree deleting dir at %s", path)
        shutil.rmtree(path, onerror=self._rmtree_error_callback)

    def _unlink(self, path):
        log.debug("unlinking %s", path)
        try:
            os.unlink(path)
        except OSError as e:
            log.debug("error %s likely because we deleted it's parent already",
                      e)

    def tearDown(self):
        super(TestCompileCommand, self).tearDown()

        self._rmtree(self.test_dir)

        # cleanup any archives we've created
        if self.cc.final_destination_path:
            log.debug("cleaning up %s", self.cc.final_destination_path)
            self._unlink(self.cc.final_destination_path)

    def test_assemble_dir_on_different_device_that_destination_dir(self):
        def faux_dirs_on_same_device(dir1, dir2):
            return False

        self.cc._dirs_on_same_device = faux_dirs_on_same_device
        self.assertRaises(InvalidCLIOptionError, self.cc.main,
                          ["--destination", self.path, "--no-archive"])

    def _assert_expected_paths_exists(self):
        tree_path = path_join(self.path, self.code)
        for expected_path in self.expected_paths:
            full_path = path_join(tree_path, expected_path)
            if os.path.exists(full_path):
                continue
            self.fail("Expected the path %s to exists in the destination path,"
                      "but it does not" % full_path)

    def _assert_unexpected_paths_do_not_exist(self, unexpected):
        tree_path = path_join(self.path, self.code)
        for unexpected_path in unexpected:
            full_path = path_join(tree_path, unexpected_path)
            if os.path.exists(full_path):
                self.fail("Expected the path %s to not exists in the destination path,"
                          "but it does." % full_path)

    # Runs the tar file creation.
    # It does not write the certs or log files because of
    # permissions. It will make those dirs in tar.
    def test_command_tar(self):
        try:
            self.cc.main(["--destination", self.path])
        except SystemExit:
            self.fail("Exception Raised")

        tar_path = path_join(self.path, "rhsm-debug-system-%s.tar.gz" % self.time_code)
        tar_file = tarfile.open(tar_path, "r")

        for expected_path in self.expected_paths:
            actual_tar_path = path_join(self.code, expected_path)
            try:
                tar_file.getmember(actual_tar_path)
            except KeyError:
                # KeyError means it wasnt in the tarfile
                self.fail("Excepted %s in tar_file, but it was not." % expected_path)

    # Runs the non-tar tree creation.
    # It does not write the certs or log files because of
    # permissions. It will make those dirs in tree.
    def test_command_tree(self):
        try:
            self.cc.main(["--destination", self.path, "--no-archive"])
        except SystemExit:
            self.fail("Exception Raised")

        self._assert_expected_paths_exists()

    # Runs the non-tar tree creation.
    # sos flag limits included data
    def test_command_sos(self):
        try:
            self.cc.main(["--destination", self.path, "--no-archive", "--sos"])
        except SystemExit:
            self.fail("Exception Raised")

        non_sos_paths = ["/etc/rhsm", "/var/log/rhsm", "/var/lib/rhsm",
                         "/etc/pki/product", "/etc/pki/entitlement",
                         "/etc/pki/consumer", "/etc/pki/product-default"]

        # TODO: these would make more sense as set()'s
        for non_sos_path in non_sos_paths:
            self.expected_paths.remove(non_sos_path)

        self._assert_expected_paths_exists()

        self._assert_unexpected_paths_do_not_exist(non_sos_paths)

    # Test to see that the filter on copy directory properly skips any -key.pem files
    def test_copy_private_key_filter(self):
        path1 = path_join(self.path, "test-key-filter")
        path2 = path_join(self.path, "result-dir")
        try:
            os.makedirs(path1)
            os.makedirs(path2)
        except os.error as e:
            # dir exists (or possibly can't be created) either of
            # which will fail shortly.
            pass

        # un monkey patch this.
        self.cc._copy_directory = self._orig_copy_directory

        try:
            open(path_join(path1, "12346.pem"), 'a').close()
            open(path_join(path1, "7890.pem"), 'a').close()
            open(path_join(path1, "22222-key.pem"), 'a').close()
            self.cc._copy_cert_directory(path1, path2)

            self.assertTrue(os.path.exists(path_join(path2, path_join(path1, "12346.pem"))))
            self.assertTrue(os.path.exists(path_join(path2, path_join(path1, "7890.pem"))))
            self.assertFalse(os.path.exists(path_join(path2, path_join(path1, "22222-key.pem"))))
        except Exception as e:
            print(e)
            raise
        finally:
            self._rmtree(path1)
            self._rmtree(path2)

    # by not creating the destination directory
    # we expect the validation to fail
    def test_archive_to_non_exist_dir(self):

        # test path is created in setup, so delete it
        os.rmdir(self.path)

        try:
            self.cc.main(["--destination", self.path])
            self.cc._validate_options()
        except InvalidCLIOptionError as e:
            self.assertEqual(six.text_type(e), "The directory specified by '--destination' must already exist.")
        else:
            self.fail("No Exception Raised")

    # method to capture code
    def _make_code(self):
        self.time_code = self._orig_make_code()
        self.code = "rhsm-debug-system-%s" % self.time_code
        return self.time_code

    def _create_assemble_dir(self, assemble_top_dir):
        assemble_dir_path = path_join(assemble_top_dir, "/%s" % datetime.now().strftime("%Y%m%d-%f"))

        assemble_paths = ["/etc/rhsm/ca", "/etc/rhsm/pluginconf.d/", "/etc/rhsm/facts",
                          "/var/log/rhsm", "/var/lib/rhsm", "/etc/pki/product",
                          "/etc/pki/entitlement", "/etc/pki/consumer",
                          "/etc/pki/product-default"]

        for assemble_path in assemble_paths:
            os.makedirs(path_join(assemble_dir_path, assemble_path))

        return assemble_dir_path

    def _get_test_dir(self):
        test_dir = tempfile.mkdtemp(suffix="-subman-unittests", prefix="test-rhsm-debug-")
        log.debug("Created testing tempdir %s", test_dir)
        return test_dir

    def _create_test_path(self, test_dir):
        path = path_join(test_dir, "testing-dir")
        self._makedir(path)
        return path

    # write to my directory instead
    def _copy_directory(self, path, prefix, ignore_pats=[]):
        shutil.copytree(path_join(self.assemble_path, path), path_join(prefix, path))

    # tests run as non-root
    def _makedir(self, dest_dir_name):
        try:
            os.makedirs(dest_dir_name)
        except Exception:
            # already there, move on
            return
