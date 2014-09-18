#
# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import mock

import fixture

from subscription_manager.model import Content, Entitlement, EntitlementSource
from subscription_manager.model.ent_cert import EntitlementCertContent
from subscription_manager.plugin.docker import action_invoker

from rhsm import certificate2

DUMMY_CERT_LOCATION = "/dummy/certs"

class TestDockerContentUpdateActionCommand(fixture.SubManFixture):

    def test_unique_paths_with_dupes(self):
        cert1 = self._mock_cert('5001')
        cert2 = self._mock_cert('5002')
        cert3 = self._mock_cert('5003')

        content1 = self._create_content('content1', cert1)
        content2 = self._create_content('content2', cert1)
        content3 = self._create_content('content3', cert2)

        # This content is provided by two other certs:
        content1_dupe = self._create_content('content1', cert2)
        content1_dupe2 = self._create_content('content1', cert3)

        contents = [content1, content2, content3, content1_dupe,
            content1_dupe2]
        cmd = action_invoker.DockerContentUpdateActionCommand(None)
        cert_paths = cmd._get_unique_paths(contents)
        self.assertEquals(6, len(cert_paths))
        self.assertTrue(cert1.path in cert_paths)
        self.assertTrue(cert1.key_path() in cert_paths)

    def _create_content(self, label, cert):
        return Content("docker", label, label, cert=cert)

    def _mock_cert(self, base_filename):
        cert = mock.Mock()
        cert.path = "%s/%s.pem" % (DUMMY_CERT_LOCATION, base_filename)
        cert.key_path.return_value = "%s/%s-key.pem" %  \
            (DUMMY_CERT_LOCATION, base_filename)
        return cert


class TestDockerContents(fixture.SubManFixture):

    def create_content(self, content_type, name):
        content = certificate2.Content(
            content_type=content_type,
            name="mock_content_%s" % name,
            label=name,
            enabled=True,
            gpg="path/to/gpg",
            url="http://mock.example.com/%s/" % name)
        return EntitlementCertContent.from_cert_content(content)

    def test_find_docker_content(self):
        yum_content = self.create_content("yum", "yum_content")
        docker_content = self.create_content("docker", "docker-content")

        ent1 = Entitlement(contents=[yum_content])
        ent2 = Entitlement(contents=[docker_content])

        ent_src = EntitlementSource()
        ent_src._entitlements = [ent1, ent2]
