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

import mock
import httplib
import socket
from M2Crypto.SSL import SSLError

import stubs
import fixture

from subscription_manager import release

versions = """
6.0
6.1
6.2
6Super
7
"""


class TestReleaseBackend(fixture.SubManFixture):
    def setUp(self):
        fixture.SubManFixture.setUp(self)
        stub_content = stubs.StubContent("c1", required_tags='rhel-6',
                                           gpg=None, enabled="1")

        # this content should be ignored since it's not enabled
        stub_content_2 = stubs.StubContent("c2", required_tags='rhel-6',
                                           gpg=None, enabled="0")

        # this should be ignored because of required_tag isn't what we
        # are looking for
        stub_content_3 = stubs.StubContent("c3", required_tags="NotAwesomeOS",
                                           gpg=None, enabled="1")

        # this should be ignored because of required_tag isn't what we
        # are looking for, and it is not enabled
        stub_content_4 = stubs.StubContent("c4", required_tags="NotAwesomeOS",
                                           gpg=None, enabled="0")

        stub_contents = [stub_content, stub_content_2, stub_content_3, stub_content_4]

        stub_product = stubs.StubProduct("rhel-6")
        stub_entitlement_certs = [stubs.StubEntitlementCertificate(stub_product,
                                                                   content=stub_contents)]
        self.stub_entitlement_dir = stubs.StubEntitlementDirectory(stub_entitlement_certs)

        self.stub_product_dir = stubs.StubProductDirectory(
            [stubs.StubProductCertificate(
                    stubs.StubProduct("rhel-6",
                                      provided_tags="rhel-6,rhel-6-stub"),)])

        def get_versions(dummy):
            return versions
        self.stub_content_connection = stubs.StubContentConnection()
        self.stub_content_connection.get_versions = get_versions

        self.rb = release.ReleaseBackend(ent_dir=self.stub_entitlement_dir,
                                         prod_dir=self.stub_product_dir,
                                         content_connection=self.stub_content_connection)

    def test_get_releases(self):
        releases = self.rb.get_releases()
        self.assertNotEquals([], releases)

    def test_get_releases_no_rhel(self):
        stub_product_dir = stubs.StubProductDirectory(
            [stubs.StubProductCertificate(
                    stubs.StubProduct("rhel-6-something",
                                      provided_tags="rhel-6-something,rhel-6-stub"),)])

        self.rb = release.ReleaseBackend(ent_dir=self.stub_entitlement_dir,
                                         prod_dir=stub_product_dir,
                                         content_connection=self.stub_content_connection)
        releases = self.rb.get_releases()
        self.assertEquals([], releases)

    def test_get_releases_rhel_no_content(self):

        stub_content_5 = stubs.StubContent("c5", required_tags="AwesomeOS",
                                           gpg=None, enabled="1")

        stub_product = stubs.StubProduct("rhel-6")
        stub_entitlement_certs = [stubs.StubEntitlementCertificate(stub_product,
                                                                   content=[stub_content_5])]

        stub_entitlement_dir = stubs.StubEntitlementDirectory(stub_entitlement_certs)
        self.rb = release.ReleaseBackend(ent_dir=stub_entitlement_dir,
                                         prod_dir=self.stub_product_dir,
                                         content_connection=self.stub_content_connection)
        releases = self.rb.get_releases()
        self.assertEquals([], releases)

    def test_get_releases_rhel_no_enabled_content(self):

        stub_content_6 = stubs.StubContent("c6", required_tags="rhel-6",
                                           gpg=None, enabled="0")

        stub_product = stubs.StubProduct("rhel-6")
        stub_entitlement_certs = [stubs.StubEntitlementCertificate(stub_product,
                                                                   content=[stub_content_6])]

        stub_entitlement_dir = stubs.StubEntitlementDirectory(stub_entitlement_certs)
        self.rb = release.ReleaseBackend(ent_dir=stub_entitlement_dir,
                                         prod_dir=self.stub_product_dir,
                                         content_connection=self.stub_content_connection)
        releases = self.rb.get_releases()
        self.assertEquals([], releases)

    def test_get_releases_throws_exception(self):
        pa = mock.patch.object(self.rb, 'content_connection')
        pa.start()
        self.stub_content_connection.get_versions.side_effect = \
                httplib.BadStatusLine("some bogus status")
        releases = self.rb.get_releases()
        self.assertEquals([], releases)

        self.stub_content_connection.get_versions.side_effect = \
                socket.error()
        releases = self.rb.get_releases()
        self.assertEquals([], releases)

        self.stub_content_connection.get_versions.side_effect = \
                SSLError()
        releases = self.rb.get_releases()
        self.assertEquals([], releases)
        pa.stop()

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
                                        "rhel-6", "notasawesome"])
        self.assertTrue(icr)

    def test_is_correct_rhel_mutliple_multiple(self):
        icr = self.rb._is_correct_rhel(["awesomeos", "rhel-6-test"],
                                       ["awesomeos", "thisthingimadeup",
                                        "rhel-6", "notasawesome"])
        self.assertTrue(icr)

    def test_is_correct_rhel_mutliple_matches_but_not_rhel(self):
        icr = self.rb._is_correct_rhel(["awesomeos", "rhel-6-test"],
                                       ["awesomeos", "thisthingimadeup",
                                        "candy", "notasawesome"])
        self.assertFalse(icr)

    def test_is_correct_rhel_content_variant_861151(self):
        icr = self.rb._is_correct_rhel(["rhel-5", "rhel-5-server"],
                                       ["rhel-5-workstation"])
        self.assertFalse(icr)

    def test_is_correct_rhel_content_rhel_5_workstation_1108257(self):
        icr = self.rb._is_correct_rhel(["rhel-5-client-workstation", "rhel-5-workstation"],
                                                    ["rhel-5-workstation"])
        self.assertTrue(icr)

    def test_is_correct_rhel_content_rhel_5_workstation_1108257_just_workstation(self):
        icr = self.rb._is_correct_rhel(["rhel-5-workstation"],
                                                    ["rhel-5-workstation"])
        self.assertTrue(icr)

    def test_is_correct_rhel_content_rhel_5_workstation_1108257_just_client_workstation(self):
        icr = self.rb._is_correct_rhel(["rhel-5-client-workstation"],
                                                    ["rhel-5-workstation"])
        self.assertFalse(icr)

    def test_is_correct_rhel_content_variant_match(self):
        icr = self.rb._is_correct_rhel(["rhel-5"],
                                       ["rhel-5-workstation"])
        self.assertFalse(icr)

    def test_is_correct_rhel_content_variant_client_workstation(self):
        icr = self.rb._is_correct_rhel(["rhel-5"],
                                                    ["rhel-5-client-workstation"])
        self.assertFalse(icr)

    def test_is_correct_rhel_content_variant_no_match(self):
        icr = self.rb._is_correct_rhel(["rhel-5-server"],
                                       ["rhel-5-workstation"])
        self.assertFalse(icr)

    def test_is_correct_rhel_content_variant_exact_match(self):
        icr = self.rb._is_correct_rhel(["rhel-5-server"],
                                       ["rhel-5-server"])
        self.assertTrue(icr)

    def test_is_correct_rhel_content_sub_variant_of_product(self):
        icr = self.rb._is_correct_rhel(["rhel-5-server"],
                                       ["rhel-5"])
        self.assertTrue(icr)

    def test_is_correct_rhel_rhel_product_no_rhel_content(self):
        icr = self.rb._is_correct_rhel(["rhel-5-server"],
                                       ["awesome-os-7"])
        self.assertFalse(icr)

    def test_build_listing_path(self):
        # /content/dist/rhel/server/6/6Server/x86_64/os/
        content_url = \
                "/content/dist/rhel/server/6/$releasever/$basearch/os/"
        listing_path = self.rb._build_listing_path(content_url)
        self.assertEquals(listing_path, "/content/dist/rhel/server/6//listing")

        # /content/beta/rhel/server/6/$releasever/$basearch/optional/os
        content_url = \
                "/content/beta/rhel/server/6/$releasever/$basearch/optional/os"
        listing_path = self.rb._build_listing_path(content_url)
        self.assertEquals(listing_path, "/content/beta/rhel/server/6//listing")
