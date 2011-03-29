#
# Copyright (c) 2010, 2011 Red Hat, Inc.
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
from subscription_manager.repolib import *
from stubs import *


class RepoTests(unittest.TestCase):
    """
    Tests for the repolib Repo class
    """

    def test_valid_label_for_id(self):
        id = 'valid-label'
        repo = Repo(id)
        self.assertEquals(id, repo.id)

    def test_invalid_label_with_spaces(self):
        id = 'label with spaces'
        repo = Repo(id)
        self.assertEquals('label-with-spaces', repo.id)

    def test_mutable_property(self):
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = 1000
        incoming_repo = {'metadata_expire': 2000}
        existing_repo.update(incoming_repo)
        self.assertEqual(1000, existing_repo['metadata_expire'])

    def test_mutable_property_in_repo_but_not_in_cert(self):
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = 1000
        incoming_repo = {}
        existing_repo.update(incoming_repo)
        self.assertEqual(1000, existing_repo['metadata_expire'])

    def test_immutable_property(self):
        existing_repo = Repo('testrepo')
        existing_repo['name'] = "meow"
        incoming_repo = {'name': "woof"}
        existing_repo.update(incoming_repo)
        self.assertEqual("woof", existing_repo['name'])

    # If the user removed a mutable property completely, or the property
    # is new in a new version of the entitlement certificate, the new value
    # should get written out.
    def test_unset_mutable_property(self):
        existing_repo = Repo('testrepo')
        incoming_repo = {'metadata_expire': 2000}
        existing_repo.update(incoming_repo)
        self.assertEqual(2000, existing_repo['metadata_expire'])

    def test_unset_immutable_property(self):
        existing_repo = Repo('testrepo')
        incoming_repo = {'name': "woof"}
        existing_repo.update(incoming_repo)
        self.assertEqual("woof", existing_repo['name'])

    # Test repo on disk has an immutable property set which has since been
    # unset in the new repo definition. This property should be removed.
    def test_set_immutable_property_now_empty(self):
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {}
        existing_repo.update(incoming_repo)
        self.assertFalse("proxy_username" in existing_repo.keys())


class UpdateActionTests(unittest.TestCase):

    def setUp(self):
        stub_prod = StubProduct("fauxprod", provided_tags="TAG1,TAG2")
        stub_prod2 = StubProduct("fauxprovidedprod", provided_tags="TAG4")
        stub_prod_cert = StubProductCertificate(stub_prod, provided_products=[stub_prod2])
        stub_prod2 = StubProduct("fauxprod2", provided_tags="TAG5,TAG6")
        stub_prod2_cert = StubProductCertificate(stub_prod2)
        stub_prod_dir = StubProductDirectory([stub_prod_cert, stub_prod2_cert])

        stub_content = [
                StubContent("c1", required_tags=""), # no required tags
                StubContent("c2", required_tags="TAG1"), 
                StubContent("c3", required_tags="TAG1,TAG2,TAG3"), # should get skipped
                StubContent("c4", required_tags="TAG1,TAG2,TAG4,TAG5,TAG6"),
        ]
        stub_ent_cert = StubEntitlementCertificate(stub_prod, content=stub_content)
        stub_ent_dir = StubCertificateDirectory([stub_ent_cert])

        self.update_action = UpdateAction(prod_dir=stub_prod_dir, 
                ent_dir=stub_ent_dir)

    def test_tags_found(self):
        content = self.update_action.get_unique_content()
        self.assertEquals(3, len(content))

