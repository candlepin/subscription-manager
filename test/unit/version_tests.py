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

from rhsm.version import Versions
import unittest

NOT_COLLECTED = "non-collected-package"


# NOTE: Because the super class will only initialize version data
# the first time an instance is created, calling the c'tor with
# different package data will not reset the data in the new instance.
# This was done on purpose so that we can test that the data is initialized
# only once.
class VersionsStub(Versions):

    def __init__(self):
        super(VersionsStub, self).__init__()
        self._collect_data()

    def _get_packages(self):
        package_set = [
            {'name': Versions.SUBSCRIPTION_MANAGER, 'version':'1', 'release': "1"},
            {'name': Versions.PYTHON_RHSM, 'version':'2', 'release': "2"},
            {'name': NOT_COLLECTED, 'version':'3', 'release': "3"},
        ]
        return package_set


class VersionsTests(unittest.TestCase):

    def test_versions_get_version_returns_correct_value(self):
        versions = VersionsStub()
        self.assertEqual('1', versions.get_version(Versions.SUBSCRIPTION_MANAGER))
        self.assertEqual('2', versions.get_version(Versions.PYTHON_RHSM))

    def test_versions_get_version_returns_empty_when_unknown(self):
        versions = VersionsStub()
        self.assertEquals("", versions.get_version("not-found"))

    def test_versions_get_release_returns_correct_value(self):
        versions = VersionsStub()
        self.assertEqual('1', versions.get_release(Versions.SUBSCRIPTION_MANAGER))
        self.assertEqual('2', versions.get_release(Versions.PYTHON_RHSM))

    def test_versions_get_release_returns_empty_when_unknown(self):
        versions = VersionsStub()
        self.assertEquals("", versions.get_release("not-found"))

    def test_versions_collects_package_data_for_only_sub_man_and_python_rhsm(self):
        versions = VersionsStub()
        self.assertEquals("", versions.get_version(NOT_COLLECTED))
