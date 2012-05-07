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

import stubs

from subscription_manager import release

versions = """
6.0
6.1
6.2
6Super
7
"""

class TestReleaseBackend(unittest.TestCase):
    def setUp(self):
        stub_content = stubs.StubContent("c1", required_tags='rhel-6',
                                           gpg=None)

        stub_contents = [stub_content]

        stub_product = stubs.StubProduct("rhel-6")
        stub_entitlement_certs = [stubs.StubEntitlementCertificate(stub_product,
                                                                   content=stub_contents)]
        stub_entitlement_dir = stubs.StubEntitlementDirectory(stub_entitlement_certs)

        stub_product_dir = stubs.StubCertificateDirectory(
            [stubs.StubProductCertificate(
                    stubs.StubProduct("rhel-6",
                                      provided_tags="rhel-6-stub"),)])

        def get_versions(dummy):
            return versions
        stub_content_connection = stubs.StubContentConnection()
        stub_content_connection.get_versions = get_versions

        self.rb = release.ReleaseBackend(ent_dir=stub_entitlement_dir,
                                         prod_dir=stub_product_dir,
                                         content_connection=stub_content_connection)

    def test_get_releases(self):
        releases = self.rb.get_releases()
        self.assertNotEquals([], releases)

    def test_is_rhel(self):
        ir = self.rb._is_rhel(["rhel-6-test"])
        self.assertTrue(ir)

    def test_is_not_rhel(self):
        ir = self.rb._is_rhel(["awesome-test"])
        self.assertFalse(ir)

    def test_is_correct_rhel(self):
        icr = self.rb._is_correct_rhel(["rhel-6-test"], ["rhel-6"])
        self.assertTrue(icr)

    def test_is_incorrect_rhel_version(self):
        icr = self.rb._is_correct_rhel(["rhel-6-test"], ["rhel-5"])
        self.assertFalse(icr)

    def test_is_incorrect_rhel(self):
        icr = self.rb._is_correct_rhel(["rhel-6-test"], ["awesomeos"])
        self.assertFalse(icr)

    def test_is_correct_rhel_wacky_tags_match(self):
        icr = self.rb._is_correct_rhel(["rhel-6-test"], ["rhel6"])
        self.assertFalse(icr)

    def test_is_correct_rhel_multiple_content(self):
        icr = self.rb._is_correct_rhel(["rhel-6-test"],
                                        ["awesomeos-", "thisthingimadeup",
                                         "rhel-6","notasawesome"])
        self.assertTrue(icr)

    def test_is_correct_rhel_mutliple_multiple(self):
        icr = self.rb._is_correct_rhel(["awesomeos", "rhel-6-test"],
                                       ["awesomeos", "thisthingimadeup",
                                        "rhel-6","notasawesome"])
        self.assertTrue(icr)

    def test_is_correct_rhel_mutliple_matches_but_not_rhel(self):
        icr = self.rb._is_correct_rhel(["awesomeos", "rhel-6-test"],
                                       ["awesomeos", "thisthingimadeup",
                                        "candy","notasawesome"])
        self.assertFalse(icr)
