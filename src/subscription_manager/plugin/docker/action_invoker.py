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
import os
import shutil

from subscription_manager import certlib

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


DOCKER_CONTENT_TYPE = "docker"


class DockerContentUpdateActionCommand(object):
    """
    UpdateActionCommand for docker configuration.

    Return a DockerContentUpdateReport.
    """
    def __init__(self, ent_source):
        self.ent_source = ent_source

    def perform(self):

        report = DockerContentUpdateActionReport()

        content_sets = self.ent_source.find_content(
            content_type=DOCKER_CONTENT_TYPE)
        unique_cert_paths = self._get_unique_paths(content_sets)

        # TODO: clean out certs that should no longer be there
        cert_dir = DockerCertDir()
        cert_dir.sync(unique_cert_paths)

        return report

    def _get_unique_paths(self, content_sets):
        """
        Return a list of unique keypairs to be copied into the
        docker certificates directory.
        """
        # Identify all the unique certificates we need to copy for docker:
        unique_cert_paths = set()
        for content in content_sets:
            print content.cert.path
            print content.cert.key_path()
            unique_cert_paths.add(
                KeyPair(content.cert.path, content.cert.key_path()))
        return unique_cert_paths


class KeyPair(object):
    """ Simple object to hold paths to an entitlement cert and key. """
    def __init__(self, cert_path, key_path):

        self.cert_path = cert_path
        self.key_path = key_path

        # Calculate the expected filenames for docker certs, just
        # re-use the base filename from entitlement cert and change
        # the file extension.
        self.dest_cert_filename = "%s.cert" %  \
            os.path.splitext(os.path.basename(self.cert_path))[0]
        # This will result in SERIAL-key.key for now, keeps it simpler:
        self.dest_key_filename = "%s.key" % \
            os.path.splitext(os.path.basename(self.key_path))[0]

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
            self.cert_path == other.cert_path and
            self.key_path == other.key_path)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "KeyPair<%s, %s>" % (self.cert_path, self.key_path)

    def __hash__(self):
        return hash(self.__repr__())


class DockerCertDir(object):
    """
    An object to manage the docker certificate directory at
    /etc/docker/certs.d.
    """

    DEFAULT_PATH = "/etc/docker/certs.d/"
    MANAGED_EXTENSIONS = [".cert", ".key"]

    def __init__(self, path=None):
        self.path = path or self.DEFAULT_PATH

    def sync(self, expected_keypairs):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        # Build up the list of certificates that should be in the
        # directory. We'll use this later to prune out any that need to
        # be cleaned up.
        expected_files = []

        for keypair in expected_keypairs:
            full_cert_path = os.path.join(self.path,
                keypair.dest_cert_filename)
            full_key_path = os.path.join(self.path,
                keypair.dest_key_filename)
            expected_files.append(keypair.dest_cert_filename)
            expected_files.append(keypair.dest_key_filename)
            if not os.path.exists(full_cert_path):
                shutil.copyfile(keypair.cert_path, full_cert_path)
            if not os.path.exists(full_key_path):
                shutil.copyfile(keypair.key_path, full_key_path)

        self._prune_old_certs(expected_files)

    def _prune_old_certs(self, expected_files):
        """
        Returns the base filenames of each file in the destination directory.
        """
        for f in os.listdir(self.path):
            fullpath = os.path.join(self.path, f)
            if os.path.isfile(fullpath) and \
                os.path.splitext(f)[1] in self.MANAGED_EXTENSIONS and \
                not f in expected_files:
                    log.info("Cleaning up docker certificate: %s" % f)
                    os.remove(fullpath)


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
