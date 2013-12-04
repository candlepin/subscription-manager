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
import tempfile
import shutil
from rhsm_debug import debug_commands
from test_managercli import TestCliCommand
from zipfile import ZipFile, ZIP_DEFLATED


class TestCompileCommand(TestCliCommand):

    command_class = debug_commands.SystemCommand

    # Runs the zip file creation.
    # It does not write the certs or log files because of
    # permissions. It will make those dirs in zip.
    def test_command(self):
        try:
            self.cc._do_command = self._orig_do_command
            self.cc._dir_to_zip = self._dir_to_zip
            path = tempfile.mkdtemp()
            self.cc.main(["--destination", path])
        except SystemExit:
            self.fail("Exception Raised")

        self.assertTrue(self.zip_file.getinfo("consumer.json") is not None)
        self.assertTrue(self.zip_file.getinfo("compliance.json") is not None)
        self.assertTrue(self.zip_file.getinfo("entitlements.json") is not None)
        self.assertTrue(self.zip_file.getinfo("pools.json") is not None)
        self.assertTrue(self.zip_file.getinfo("subscriptions.json") is not None)
        self.assertTrue(self.zip_file.getinfo("etc/rhsm/rhsm.conf") is not None)
        self.assertTrue(self.zip_file.getinfo("var/log/rhsm/") is not None)
        self.assertTrue(self.zip_file.getinfo("etc/pki/product/") is not None)
        self.assertTrue(self.zip_file.getinfo("etc/pki/entitlement/") is not None)
        # cannot test for this. an unregistered system will fail
        # self.assertTrue(self.zip_file.getinfo("etc/pki/consumer/") is not None)
        shutil.rmtree(path)

    # fake method to avoid permission issues
    def _dir_to_zip(self, directory, zipfile):
        self.zip_file = zipfile
        for dirname, subdirs, files in os.walk(directory):
            zipfile.write(dirname)

    # test the real dir_to_zip method
    def test_dir_to_zip(self):
        zip_dir = tempfile.mkdtemp()
        zip_temp = os.path.join(zip_dir, "test-%s.zip" % self.cc._make_code())
        zip_file = ZipFile(zip_temp, "w", ZIP_DEFLATED)
        file_dir = tempfile.mkdtemp()

        self.cc._write_flat_file(file_dir, "file1", "file1-content")
        self.cc._write_flat_file(file_dir, "file2", "file2-content")
        self.cc._write_flat_file(file_dir, "file3", "file3-content")
        self.cc._dir_to_zip(file_dir, zip_file)

        file_dir_str = str.lstrip(file_dir, "/")
        self.assertTrue(zip_file.getinfo(os.path.join(file_dir_str, "file1")) is not None)
        self.assertTrue(zip_file.getinfo(os.path.join(file_dir_str, "file1")).file_size > 0)
        self.assertTrue(zip_file.getinfo(os.path.join(file_dir_str, "file2")) is not None)
        self.assertTrue(zip_file.getinfo(os.path.join(file_dir_str, "file2")).file_size > 0)
        self.assertTrue(zip_file.getinfo(os.path.join(file_dir_str, "file3")) is not None)
        self.assertTrue(zip_file.getinfo(os.path.join(file_dir_str, "file3")).file_size > 0)

        shutil.rmtree(file_dir)
        shutil.rmtree(zip_dir)
