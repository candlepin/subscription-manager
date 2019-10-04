from __future__ import print_function, division, absolute_import

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
import logging
import os
import re
import shutil

from subscription_manager import certlib
from subscription_manager.model import find_content

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

CONTAINER_CONTENT_TYPE = "containerimage"

RH_CDN_REGEX = re.compile('^cdn\.(?:.*\.)?redhat\.com$')
RH_CDN_CA = "/etc/rhsm/ca/redhat-entitlement-authority.pem"


class ContainerContentUpdateActionCommand(object):
    """
    UpdateActionCommand for Docker configuration.

    Return a ContainerContentUpdateReport.
    """
    def __init__(self, ent_source, registry_hostnames, host_cert_dir):
        self.ent_source = ent_source
        self.registry_hostnames = registry_hostnames
        self.host_cert_dir = host_cert_dir

    def perform(self):

        report = ContainerUpdateReport()

        content_sets = self._find_content()
        log.debug("Got content_sets: %s" % content_sets)
        unique_cert_paths = self._get_unique_paths(content_sets)

        for registry_hostname in self.registry_hostnames:
            cert_dir = ContainerCertDir(report=report,
                registry=registry_hostname,
                host_cert_dir=self.host_cert_dir)
            cert_dir.sync(unique_cert_paths)

        return report

    def _find_content(self):
        return find_content(self.ent_source,
            content_type=CONTAINER_CONTENT_TYPE)

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
        # We use the base filename from the cert so avoid the SERIAL-key
        # we would have with our normal entitlement certs. We need the
        # base filename to be the same for both .cert and .key.
        self.dest_key_filename = "%s.key" % \
            os.path.splitext(os.path.basename(self.cert_path))[0]

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

    # We will presume to manage files with these extensions in the
    # hostname directory we're dealing with. Any unexpected files with
    # these extensions will be removed. Any other files will be left
    # alone.
    MANAGED_EXTENSIONS = [".cert", ".key"]

    def __init__(self, report, registry, host_cert_dir):
        self.report = report
        self.registry = registry

        # This is the overall cert directory where hostname specific
        # subdirectories will go:
        self.host_cert_dir = host_cert_dir

        # The final hostname specific cert directory we'll sync to:
        self.path = os.path.join(self.host_cert_dir, registry)

    def sync(self, expected_keypairs):
        log.debug("Syncing container certificates to %s" % self.path)
        if not os.path.exists(self.host_cert_dir):
            log.warn("Container cert directory does not exist: %s" % self.host_cert_dir)
            log.warn("Exiting plugin")
            return
        if not os.path.exists(self.path):
            log.info("Container cert directory does not exist, creating it.")
            os.mkdir(self.path)

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
            # WARNING: We assume that matching filenames must be the same
            # certificate and key. Because we use serials in the filename, this
            # should be safe.
            if not os.path.exists(full_cert_path):
                log.info("Copying: %s -> %s" %
                    (keypair.cert_path, full_cert_path))
                shutil.copyfile(keypair.cert_path, full_cert_path)
                shutil.copymode(keypair.cert_path, full_cert_path)
                self.report.added.append(full_cert_path)
            if not os.path.exists(full_key_path):
                log.info("Copying: %s -> %s" %
                    (keypair.key_path, full_key_path))
                shutil.copyfile(keypair.key_path, full_key_path)
                shutil.copymode(keypair.key_path, full_key_path)
                self.report.added.append(full_key_path)

        self._prune_old_certs(expected_files)

        # If we see something that looks like Red Hat's CDN, we know we need
        # to symlink the python-rhsm delivered CA cert in:
        if RH_CDN_REGEX.match(os.path.basename(self.path)):
            if not self._rh_cdn_ca_exists():
                log.error("Detected a CDN hostname, but no CA certificate installed.")
            else:
                outfile = "%s.crt" % os.path.splitext(os.path.basename(RH_CDN_CA))[0]
                ca_symlink = os.path.join(self.path, outfile)
                if not os.path.exists(ca_symlink):
                    os.symlink(RH_CDN_CA, ca_symlink)
                    log.info("Created symlink: %s -> %s" % (ca_symlink, RH_CDN_CA))

    def _rh_cdn_ca_exists(self):
        """
        Check if the python-rhsm delivered CA PEM exists.
        """
        # Separate method for testing purposes.
        return os.path.exists(RH_CDN_CA)

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
