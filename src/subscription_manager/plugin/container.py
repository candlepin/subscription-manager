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

""" Core code for the container content plugin. """

import gettext
import logging
import os
import shutil

from subscription_manager import certlib

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


CONTAINER_CONTENT_TYPE = "containerImage"


class ContainerContentUpdateActionCommand(object):
    """
    UpdateActionCommand for Docker configuration.

    Return a ContainerContentUpdateReport.
    """
    def __init__(self, ent_source, registry):
        self.ent_source = ent_source
        self.registry = registry

    def perform(self):

        report = ContainerUpdateReport()

        content_sets = self.ent_source.find_content(
            content_type=CONTAINER_CONTENT_TYPE)
        unique_cert_paths = self._get_unique_paths(content_sets)

        cert_dir = ContainerCertDir(report=report, registry=self.registry)
        cert_dir.sync(unique_cert_paths)

        return report

    def _get_unique_paths(self, content_sets):
        """
        Return a list of unique keypairs to be copied into the
        docker certificates directory.
        """
        # Identify all the unique certificates we need to copy:
        unique_cert_paths = set()
        for content in content_sets:
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


class ContainerCertDir(object):
    """
    An object to manage the docker certificate directory at
    /etc/docker/certs.d/.
    """

    DEFAULT_PATH = "/etc/docker/certs.d/"

    # We will presume to manage files with these extensions in the
    # hostname directory we're dealing with. Any unexpected files with
    # these extensions will be removed. Any other files will be left
    # alone.
    MANAGED_EXTENSIONS = [".cert", ".key"]

    def __init__(self, report, registry, path=None):
        self.report = report
        self.registry = registry
        self.path = path or self.DEFAULT_PATH
        self.path = os.path.join(self.path, registry)

    def sync(self, expected_keypairs):
        log.debug("Syncing container certificates to %s" % self.path)
        if not os.path.exists(self.path):
            log.info("Container cert directory does not exist, creating it.")
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
                log.info("Copying: %s -> %s" %
                    (keypair.cert_path, full_cert_path))
                shutil.copyfile(keypair.cert_path, full_cert_path)
                self.report.added.append(full_cert_path)
            if not os.path.exists(full_key_path):
                log.info("Copying: %s -> %s" %
                    (keypair.key_path, full_key_path))
                shutil.copyfile(keypair.key_path, full_key_path)
                self.report.added.append(full_key_path)

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
                    log.info("Cleaning up old certificate: %s" % f)
                    os.remove(fullpath)
                    self.report.removed.append(fullpath)


class ContainerUpdateReport(certlib.ActionReport):
    """Track container cert changes."""
    name = "Container certificate updates report"

    def __init__(self):
        super(ContainerUpdateReport, self).__init__()
        # Full path to certs/keys we added:
        self.added = []

        # Full path to cert/keys we cleaned up:
        self.removed = []

    def updates(self):
        """ Number of updates. """
        return len(self.added) + len(self.removed)

    def _format_file_list(self, file_list):
        s = []
        for filename in file_list:
            s.append(file_list)
        return '\n'.join(s)

    def __str__(self):
        s = ["Container content cert updates\n"]
        s.append(_("Added:"))
        s.append(self._format_file_list(self.added))
        s.append(_("Removed:"))
        s.append(self._format_file_list(self.removed))
        return '\n'.join(s)
