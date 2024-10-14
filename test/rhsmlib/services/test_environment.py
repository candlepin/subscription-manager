# Copyright (c) 2017 Red Hat, Inc.
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
from unittest import mock

from test.rhsmlib.base import InjectionMockingTest

from rhsm import connection

from rhsmlib.services import environment


ENVIRONMENTS_JSON = [
    {
        "created": "2024-10-03T18:12:56+0000",
        "updated": "2024-10-03T18:12:56+0000",
        "id": "8bdf14cf9e534119a1fe617c03304768",
        "name": "template 1",
        "type": "content-template",
        "description": "my template",
        "owner": {
            "id": "8ad980939253781c01925378340e0002",
            "key": "content-sources-test",
            "displayName": "ContentSourcesTest",
            "href": "/owners/content-sources-test",
            "contentAccessMode": "org_environment"
        },
        "environmentContent": [
            {
                "contentId": "11055",
                "enabled": True
            },
            {
                "contentId": "56a3a98c76ea4e16bd68424a2c9cc1c1",
                "enabled": True
            },
            {
                "contentId": "11049",
                "enabled": True
            },
        ]
    },
    {
        "created": "2024-10-09T19:08:14+0000",
        "updated": "2024-10-09T19:08:14+0000",
        "id": "6c62889601be41128fe2fece53141fd4",
        "name": "template 2",
        "type": "content-template",
        "description": "my template",
        "owner": {
            "id": "8ad980939253781c01925378340e0002",
            "key": "content-sources-test",
            "displayName": "ContentSourcesTest",
            "href": "/owners/content-sources-test",
            "contentAccessMode": "org_environment"
        },
        "environmentContent": [
            {
                "contentId": "11055",
                "enabled": True
            },
            {
                "contentId": "11049",
                "enabled": True
            },
        ]
    }
]


class TestEnvironmentService(InjectionMockingTest):
    def setUp(self):
        super(TestEnvironmentService, self).setUp()
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")

    def injection_definitions(self, *args, **kwargs):
        return None

    def test_list_environments(self):
        self.mock_cp.getEnvironmentList.return_value = ENVIRONMENTS_JSON

        result = environment.EnvironmentService(self.mock_cp).list("org")
        self.assertEqual(ENVIRONMENTS_JSON, result)

    def test_list_environments_without_typed_environments(self):
        self.mock_cp.getEnvironmentList.return_value = ENVIRONMENTS_JSON

        result = environment.EnvironmentService(self.mock_cp).list("org", typed_environments=False)
        self.assertEqual(ENVIRONMENTS_JSON, result)
