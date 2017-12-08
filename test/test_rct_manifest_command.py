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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import errno
import mock
import os
import shutil
import six
import tempfile
import zipfile
from zipfile import ZipFile

from subscription_manager.i18n_optparse import OptionParser

from . import manifestdata
from rct.manifest_commands import CatManifestCommand
from rct.manifest_commands import DumpManifestCommand
from rct.manifest_commands import get_value
from rct.manifest_commands import RCTManifestCommand
from rct.manifest_commands import ZipExtractAll

from .fixture import Capture, SubManFixture


def _build_valid_manifest():
    manifest_zip = six.BytesIO()
    manifest_object = ZipFile(manifest_zip, "w", compression=zipfile.ZIP_STORED)
    manifest_object.writestr("signature", "dummy")
    consumer_export_zip = six.BytesIO()
    consumer_export_object = ZipFile(consumer_export_zip, "w", compression=zipfile.ZIP_STORED)
    consumer_export_object.writestr("export/consumer.json", manifestdata.consumer_json)
    consumer_export_object.writestr("export/meta.json", manifestdata.meta_json)
    consumer_export_object.writestr("export/entitlements/8a99f9833cf86efc013cfd613be066cb.json",
            manifestdata.entitlement_json)
    consumer_export_object.writestr("export/entitlement_certificates/2414805806930829936.pem",
            manifestdata.ent_cert + '\n' + manifestdata.ent_cert_private)
    consumer_export_object.close()
    manifest_object.writestr("consumer_export.zip", consumer_export_zip.getvalue())
    manifest_object.close()
    return manifest_zip


class RCTManifestCommandTests(SubManFixture):

    def test_get_value(self):
        data = {"test": "value", "test2": {"key2": "value2", "key3": []}}
        self.assertEqual("", get_value(data, "some.test"))
        self.assertEqual("", get_value(data, ""))
        self.assertEqual("", get_value(data, "test2.key4"))
        self.assertEqual("", get_value(data, "test2.key2.fred"))
        self.assertEqual("value", get_value(data, "test"))
        self.assertEqual("value2", get_value(data, "test2.key2"))
        self.assertEqual([], get_value(data, "test2.key3"))

    def test_cat_manifest(self):
        catman = CatManifestCommand()
        parser = OptionParser()
        parser.add_option("--no-content")
        (options, args) = parser.parse_args([])
        catman.options = options
        catman.args = [_build_valid_manifest()]

        with Capture() as cap:
            catman._do_command()

        self.assertEqual("", cap.err)
        self.assert_string_equals(manifestdata.correct_manifest_output, cap.out)

    def test_extract_manifest(self):
        tmp_dir = tempfile.mkdtemp()
        mancommand = RCTManifestCommand()
        mancommand.args = [_build_valid_manifest()]
        mancommand._extract_manifest(tmp_dir)

        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "export")))

        shutil.rmtree(tmp_dir)

    def test_dump_manifest_current(self):
        original_directory = os.getcwd()
        new_directory = tempfile.mkdtemp()
        os.chdir(new_directory)
        mancommand = DumpManifestCommand()
        mancommand.args = [_build_valid_manifest()]

        #This makes sure there is a 'None' at 'self.options.destination'
        mancommand.options = mancommand
        mancommand.destination = None
        mancommand.overwrite_files = False

        mancommand._do_command()
        self.assertTrue(os.path.exists(os.path.join(new_directory, "export")))
        os.chdir(original_directory)
        shutil.rmtree(new_directory)

    def test_dump_manifest_directory(self):
        new_directory = tempfile.mkdtemp()
        mancommand = DumpManifestCommand()
        mancommand.args = [_build_valid_manifest()]

        #This makes sure the temp directory is referenced at 'self.options.destination'
        mancommand.options = mancommand
        mancommand.destination = new_directory
        mancommand.overwrite_files = False

        mancommand._do_command()
        self.assertTrue(os.path.exists(os.path.join(new_directory, "export")))
        shutil.rmtree(new_directory)

    def test_dump_manifest_directory_twice(self):
        new_directory = tempfile.mkdtemp()
        mancommand = DumpManifestCommand()
        mancommand.args = [_build_valid_manifest()]

        #This makes sure the temp directory is referenced at 'self.options.destination'
        mancommand.options = mancommand
        mancommand.destination = new_directory
        mancommand.overwrite_files = True

        mancommand._do_command()
        mancommand._do_command()
        self.assertTrue(os.path.exists(os.path.join(new_directory, "export")))
        shutil.rmtree(new_directory)

    @mock.patch("rct.manifest_commands.ZipExtractAll._write_file")
    def test_dump_manifest_directory_no_perms(self, mock_write_file):
        new_directory = tempfile.mkdtemp()
        mancommand = DumpManifestCommand()
        mancommand.args = [_build_valid_manifest()]

        #This makes sure the temp directory is referenced at 'self.options.destination'
        mancommand.options = mancommand
        mancommand.destination = new_directory
        mancommand.overwrite_files = True

        mock_write_file.side_effect = IOError(errno.EACCES, "permission denied", new_directory)
        mancommand._do_command()
        # we fail to extract manifest in this case
        self.assertFalse(os.path.exists(os.path.join(new_directory, "export")))

    @mock.patch("rct.manifest_commands.ZipExtractAll._write_file")
    def test_dump_manifest_directory_exists(self, mock_write_file):
        new_directory = tempfile.mkdtemp()

        mancommand = DumpManifestCommand()
        mancommand.args = [_build_valid_manifest()]

        #This makes sure the temp directory is referenced at 'self.options.destination'
        mancommand.options = mancommand
        mancommand.destination = new_directory
        mancommand.overwrite_files = True

        mock_write_file.side_effect = OSError(errno.EEXIST, "file exists", new_directory)
        mancommand._do_command()
        # we fail to extract manifest in this case
        self.assertFalse(os.path.exists(os.path.join(new_directory, "export")))


class RCTManifestExtractTests(unittest.TestCase):

    def test_extractall_outside_base(self):
        zip_file_object = six.BytesIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr("../../../../wat", "this is weird")

        tmp_dir = tempfile.mkdtemp()
        self.assertRaises(Exception, archive.extractall, (tmp_dir))
        archive.close()
        shutil.rmtree(tmp_dir)

    def test_extractall_net_path(self):
        zip_file_object = six.BytesIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr(r"\\nethost\share\whatever", "this is weird")

        archive.close()
        archive = ZipExtractAll(zip_file_object, "r", compression=zipfile.ZIP_STORED)

        tmp_dir = tempfile.mkdtemp()
        archive.extractall(tmp_dir)
        archive.close()

        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "\\\\nethost\\share\\whatever")))

        shutil.rmtree(tmp_dir)

    def test_extractall_local(self):
        zip_file_object = six.BytesIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr("./some/path", "this is okay I think, though odd")

        archive.close()
        archive = ZipExtractAll(zip_file_object, "r", compression=zipfile.ZIP_STORED)

        tmp_dir = tempfile.mkdtemp()
        archive.extractall(tmp_dir)
        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "./some/path")))
        archive.close()
        shutil.rmtree(tmp_dir)

    @mock.patch("sys.exit")
    def test_extractall_nonzip(self, mock_exit):
        not_zip_file_object = six.BytesIO()
        ZipExtractAll(not_zip_file_object, "r")
        mock_exit.assert_called_with(1)
