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
import os
from cStringIO import StringIO

from rct.manifest_commands import get_value
from rct.manifest_commands import ZipExtractAll
from rct.manifest_commands import RCTManifestCommand


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

    def test_extractall_outside_base(self):
        zip_file_object = StringIO()
        archive = ZipExtractAll(zip_file_object, "w", compression=zipfile.ZIP_STORED)
        archive.writestr("../../../../wat", "this is weird")
        archive.close()

        tmp_dir = tempfile.mkdtemp()
        self.assertRaises(Exception, archive.extractall, (tmp_dir))

        shutil.rmtree(tmp_dir)

    def test_extract_manifest(self):
        zip_file_object1 = StringIO()
        archive1 = ZipExtractAll(zip_file_object1, "w", compression=zipfile.ZIP_STORED)
        archive1.writestr("signature", "dummy signature")

        zip_file_object2 = StringIO()
        archive2 = ZipExtractAll(zip_file_object2, "w", compression=zipfile.ZIP_STORED)
        archive2.writestr("export/consumer.json", "dummy json")
        archive2.close()

        archive1.writestr("consumer_export.zip", zip_file_object2.getvalue())
        archive1.close()

        tmp_dir = tempfile.mkdtemp()
        mancommand = RCTManifestCommand()
        mancommand.args = [zip_file_object1]
        mancommand._extract_manifest(tmp_dir)

        self.assertTrue(os.path.exists(os.path.join(tmp_dir, "export")))

        shutil.rmtree(tmp_dir)
