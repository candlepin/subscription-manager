from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2020 Red Hat, Inc.
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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import patch
import tempfile
import shutil
import os

from rhsmlib.facts import kpatch


class TestKPatchCollector(unittest.TestCase):
    def setUp(self):
        self.DIR_WITH_INSTALLED_KPATCH_MODULES = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.DIR_WITH_INSTALLED_KPATCH_MODULES, "3.10.0-1062.el7.x86_64"))
        os.mkdir(os.path.join(self.DIR_WITH_INSTALLED_KPATCH_MODULES, "3.10.0-1062.1.1.el7.x86_64"))
        os.mkdir(os.path.join(self.DIR_WITH_INSTALLED_KPATCH_MODULES, "3.10.0-1062.1.2.el7.x86_64"))
        self.DIRS_WITH_LOADED_MODULE = [
            "/path/to/not-existing-directory",
            tempfile.mkdtemp()
        ]
        os.mkdir(os.path.join(self.DIRS_WITH_LOADED_MODULE[1], "3.10.0-1062.el7.x86_64"))

    def tearDown(self):
        shutil.rmtree(self.DIRS_WITH_LOADED_MODULE[1])
        shutil.rmtree(self.DIR_WITH_INSTALLED_KPATCH_MODULES)

    @patch('rhsmlib.facts.kpatch.which')
    def test_kpatch_is_not_installed(self, which):
        which.return_value = None
        collector = kpatch.KPatchCollector()
        kpatch_facts = collector.get_all()
        self.assertEqual(kpatch_facts, {})

    @patch('rhsmlib.facts.kpatch.which')
    def test_get_kpatch_facts(self, which):
        which.return_value = '/usr/sbin/kpatch'
        collector = kpatch.KPatchCollector()
        collector.DIR_WITH_INSTALLED_KPATCH_MODULES = self.DIR_WITH_INSTALLED_KPATCH_MODULES
        collector.DIRS_WITH_LOADED_MODULE = self.DIRS_WITH_LOADED_MODULE
        kpatch_facts = collector.get_all()
        self.assertIn('kpatch.loaded', kpatch_facts)
        self.assertEqual(kpatch_facts['kpatch.loaded'], '3.10.0-1062.el7.x86_64')
        self.assertIn('kpatch.installed', kpatch_facts)
        installed_kpatches = sorted(kpatch_facts['kpatch.installed'].split())
        self.assertEqual(len(installed_kpatches), 3)
        self.assertEqual(
            installed_kpatches,
            ['3.10.0-1062.1.1.el7.x86_64', '3.10.0-1062.1.2.el7.x86_64', '3.10.0-1062.el7.x86_64']
        )
