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

import unittest
import tempfile
import shutil
import zipfile
from zipfile import ZipFile
import os
import sys
from cStringIO import StringIO
import manifestdata
from rct.manifest_commands import get_value
from rct.manifest_commands import ZipExtractAll
from rct.manifest_commands import RCTManifestCommand
from rct.manifest_commands import CatManifestCommand
from stubs import MockStdout, MockStderr


def _build_valid_manifest():
    manifest_zip = StringIO()
    manifest_object = ZipFile(manifest_zip, "w", compression=zipfile.ZIP_STORED)
    manifest_object.writestr("signature", "dummy")
    consumer_export_zip = StringIO()
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


class RCTManifestCommandTests(unittest.TestCase):

    def test_get_value(self):
        data = {"test": "value", "test2": {"key2": "value2", "key3": []}}
        self.assertEquals("", get_value(data, "some.test"))
        self.assertEquals("", get_value(data, ""))
        self.assertEquals("", get_value(data, "test2.key4"))
        self.assertEquals("", get_value(data, "test2.key2.fred"))
        self.assertEquals("value", get_value(data, "test"))
        self.assertEquals("value2", get_value(data, "test2.key2"))
        self.assertEquals([], get_value(data, "test2.key3"))

    def test_cat_manifest(self):
        catman = CatManifestCommand()
        catman.args = [_build_valid_manifest()]

        mock_out = MockStdout()
        mock_err = MockStderr()
        sys.stdout = mock_out
        sys.stderr = mock_err

        catman._do_command()

        self.assertEquals("", mock_err.buffer)
        self.assertEquals(manifestdata.correct_manifest_output, mock_out.buffer)

        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def test_extract_manifest(self):
        tmp_dir = tempfile.mkdtemp()
        mancommand = RCTManifestCommand()
        mancommand.args = [_build_valid_manifest()]
        mancommand._extract_manifest(tmp_dir)

        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "export")))

        shutil.rmtree(tmp_dir)


class RCTManifestExtractTests(unittest.TestCase):

    def test_extractall_outside_base(self):
        zip_file_object = StringIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr("../../../../wat", "this is weird")

        tmp_dir = tempfile.mkdtemp()
        self.assertRaises(Exception, archive.extractall, (tmp_dir))
        archive.close()
        shutil.rmtree(tmp_dir)

    def test_extractall_net_path(self):
        zip_file_object = StringIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr(r"\\nethost\share\whatever", "this is weird")

        tmp_dir = tempfile.mkdtemp()
        archive.extractall(tmp_dir)
        archive.close()

        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "\\\\nethost\\share\\whatever")))

        shutil.rmtree(tmp_dir)

    def test_extractall_local(self):
        zip_file_object = StringIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr("./some/path", "this is okay I think, though odd")

        tmp_dir = tempfile.mkdtemp()
        archive.extractall(tmp_dir)
        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "./some/path")))
        archive.close()
        shutil.rmtree(tmp_dir)
