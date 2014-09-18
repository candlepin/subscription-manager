#
# Copyright (c) 2014 Red Hat, Inc.
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

""" Core code for the docker content plugin. """

import gettext
import logging

from subscription_manager import certlib

# plugins get
log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


DOCKER_CONTENT_TYPE = "docker"
DOCKER_CERT_DIR = "/etc/docker/certs.d"


class DockerContentUpdateActionCommand(object):
    """
    UpdateActionCommand for docker configuration.

    Return a DockerContentUpdateReport.
    """
    def __init__(self, ent_source):
        self.ent_source = ent_source

    def perform(self):

        report = DockerContentUpdateActionReport()

        content_sets = self.ent_source.find_content(content_type=DOCKER_CONTENT_TYPE)
        unique_cert_paths = self._get_unique_paths(content_sets)

        # TODO: clean out certs that should no longer be there

        return report

    def _get_unique_paths(self, content_sets):
        """
        Return a list of unique cert and key paths to be copied into the
        docker certificates directory.
        """
        # Identify all the unique certificates we need to copy for docker:
        unique_cert_paths = set()
        for content in content_sets:
            print content.cert.path
            print content.cert.key_path()
            unique_cert_paths.add(content.cert.path)
            unique_cert_paths.add(content.cert.key_path())
        return unique_cert_paths


class DockerContentUpdateActionReport(certlib.ActionReport):
    """Track ostree repo config changes."""
    name = "Ostree repo updates report"

    def __init__(self):
        super(DockerContentUpdateActionReport, self).__init__()
        self.orig_remotes = []
        self.remote_updates = []
        self.remote_added = []
        self.remote_deleted = []
        self.content_to_remote = {}

    def updates(self):
        """Number of updates. Approximately."""
        return len(self.remote_updates)

    def _format_remotes(self, remotes):
        s = []
        for remote in remotes:
            s.append(remote.report())
        return '\n'.join(s)

    def __str__(self):
        s = ["Docker repo updates\n"]
        s.append(_("Updates:"))
        s.append(self._format_remotes(self.remote_updates))
        s.append(_("Added:"))
        s.append(self._format_remotes(self.remote_updates))
        s.append(_("Deleted:"))
        s.append(self._format_remotes(self.orig_remotes))
        return '\n'.join(s)
