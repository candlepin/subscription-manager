#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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

import errno
import gettext
import os
import sys
import shutil
import logging
import tarfile
from datetime import datetime

import subscription_manager.injection as inj
import subscription_manager.managercli as managercli
from subscription_manager.managercli import CliCommand
from subscription_manager.cli import InvalidCLIOptionError
from rhsm import ourjson as json
from rhsm.config import initConfig

_ = gettext.gettext

cfg = initConfig()

log = logging.getLogger('rhsm-app.' + __name__)

NOT_REGISTERED = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")

ASSEMBLE_DIR = '/var/spool/rhsm/debug'
ROOT_READ_ONLY = 0600
KEY_IGNORE_PATS = ['key.pem']


class SystemCommand(CliCommand):

    def __init__(self, name="system",
                 shortdesc=_("Assemble system information as a tar file or directory"),
                 primary=True):
        CliCommand.__init__(self, name=name, shortdesc=shortdesc, primary=primary)

        self.parser.add_option("--destination", dest="destination",
                               default="/tmp", help=_("the destination location of the result; default is /tmp"))
        # default is to build an archive, this skips the archive and clean up,
        # just leaving the directory of debug info for sosreport to report
        self.parser.add_option("--no-archive", action='store_false',
                               default=True, dest="archive",
                               help=_("data will be in an uncompressed directory"))
        self.parser.add_option("--sos", action='store_true',
                               default=False, dest="sos",
                               help=_("only data not already included in sos report will be collected"))

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] ") % self.name

    def _validate_options(self):
        if self.options.destination and self.options.archive:
            if not os.path.exists(self.options.destination):
                raise InvalidCLIOptionError(_("The destination directory for the archive must already exist."))

    def _do_command(self):
        self._validate_options()
        consumer = inj.require(inj.IDENTITY)
        if not consumer.is_valid():
            print NOT_REGISTERED
            sys.exit(-1)

        code = self._make_code()
        assemble_path = self._get_assemble_dir()
        archive_name = "rhsm-debug-system-%s" % code
        tar_file_name = "%s.tar.gz" % archive_name
        # /var/log/rhsm/debuf/rhsm-debug-system-20131212-121234/
        content_path = os.path.join(assemble_path, archive_name)
        # /var/log/rhsm/debug/rhsm-debug-system-20131212-123413.tar.gz
        tar_file_path = os.path.join(assemble_path, tar_file_name)

        try:
            try:
                # assemble path is in the package, so should always exist
                self._makedir(content_path)

                owner = self.cp.getOwner(consumer.uuid)

                try:
                    self._write_flat_file(content_path, "subscriptions.json",
                                          self.cp.getSubscriptionList(owner['key']))
                except Exception, e:
                    log.warning("Server does not allow retrieval of subscriptions by owner.")

                self._write_flat_file(content_path, "consumer.json",
                                      self.cp.getConsumer(consumer.uuid))
                self._write_flat_file(content_path, "compliance.json",
                                      self.cp.getCompliance(consumer.uuid))
                self._write_flat_file(content_path, "entitlements.json",
                                      self.cp.getEntitlementList(consumer.uuid))
                self._write_flat_file(content_path, "pools.json",
                                      self.cp.getPoolsList(consumer.uuid, True, None, owner['key']))
                self._write_flat_file(content_path, "version.json",
                                      self._get_version_info())

                # FIXME: we need to anon proxy passwords?
                sos = self.options.sos
                defaults = cfg.defaults()
                # sosreport collects /etc/rhsm/* and /var/*/rhsm/*, so these would
                # be redundant for sos
                if not sos:
                    # copy rhsm.conf specifically
                    self._copy_cert_directory("/etc/rhsm", content_path)
                    self._copy_directory('/var/log/rhsm', content_path)
                    self._copy_directory('/var/lib/rhsm', content_path)

                if defaults['productcertdir'] != cfg.get('rhsm', 'productCertDir') or not sos:
                    self._copy_cert_directory(cfg.get('rhsm', 'productCertDir'), content_path)

                if defaults['entitlementcertdir'] != cfg.get('rhsm', 'entitlementCertDir') or not sos:
                    self._copy_cert_directory(cfg.get('rhsm', 'entitlementCertDir'), content_path)

                if defaults['consumercertdir'] != cfg.get('rhsm', 'consumerCertDir') or not sos:
                    self._copy_cert_directory(cfg.get('rhsm', 'consumerCertDir'), content_path)

                # If ca_cert_dir and pluginconfdif are configured as subdirs of /etc/rhsm
                # (as is the default) we will have already copied there contents,
                # so ignore directory exists errors
                try:
                    if defaults['ca_cert_dir'] != cfg.get('rhsm', 'ca_cert_dir') or not sos:
                        self._copy_cert_directory(cfg.get('rhsm', 'ca_cert_dir'), content_path)
                except EnvironmentError, e:
                    if e.errno != errno.EEXIST:
                        raise

                try:
                    if defaults['pluginconfdir'] != cfg.get('rhsm', 'pluginconfdir') or not sos:
                        self._copy_directory(cfg.get('rhsm', 'pluginconfdir'), content_path)
                except EnvironmentError, e:
                    if e.errno != errno.EEXIST:
                        raise

                # build an archive by default
                if self.options.archive:
                    try:
                        tf = tarfile.open(tar_file_path, "w:gz")
                        tf.add(content_path, archive_name)
                    finally:
                        tf.close()

                    final_path = os.path.join(self.options.destination, "rhsm-debug-system-%s.tar.gz" % code)
                    sfm = SaferFileMove()
                    sfm.move(tar_file_path, final_path)
                    print _("Wrote: %s") % final_path
                else:
                    # NOTE: this will fail across filesystems. We could add a force
                    # flag to for creation of a specific name with approriate
                    # warnings.
                    dest_dir_name = os.path.join(self.options.destination, archive_name)

                    # create the dest dir, and set it's perms, this is atomic ish
                    self._makedir(dest_dir_name)

                    # try to rename the dir atomically
                    # rename only works on the same filesystem, but it is atomic.
                    os.rename(content_path, dest_dir_name)

                    print _("Wrote: %s/%s") % (self.options.destination, archive_name)

            except Exception, e:
                managercli.handle_exception(_("Unable to create zip file of system information: %s") % e, e)
        finally:
            if assemble_path and os.path.exists(assemble_path):
                shutil.rmtree(assemble_path, True)

    def _make_code(self):
        return datetime.now().strftime("%Y%m%d-%S")

    def _get_version_info(self):
        return {"server type": self.server_versions["server-type"],
                "subscription management server": self.server_versions["candlepin"],
                "subscription-manager": self.client_versions["subscription-manager"],
                "python-rhsm": self.client_versions["python-rhsm"]}

    def _write_flat_file(self, content_path, filename, content):
        path = os.path.join(content_path, filename)
        try:
            fo = open(path, "w+")
            fo.write(json.dumps(content, indent=4, sort_keys=True))
        finally:
            fo.close()

    def _copy_tree(self, src, dst, blacklist=[]):
        if os.path.isdir(src):
            if not os.path.exists(dst):
                self._makedir(dst)
            for fname in os.listdir(src):
                stop = False
                for item in blacklist or []:
                    if fname.endswith(item):
                        stop=True
                        break
                if not stop:
                    self._copy_tree(os.path.join(src, fname), os.path.join(dst, fname), blacklist)
        else:
            shutil.copyfile(src, dst)

    def _copy_directory(self, src_path, dest_path, ignore_pats=[]):
        rel_path = src_path
        if os.path.isabs(src_path):
            rel_path = src_path[1:]

        self._copy_tree(src_path, os.path.join(dest_path, rel_path), ignore_pats)

    def _copy_cert_directory(self, src_path, dest_path):
        self._copy_directory(src_path,
                             dest_path,
                             KEY_IGNORE_PATS)

    def _get_assemble_dir(self):
        return ASSEMBLE_DIR

    def _makedir(self, dest_dir_name):
        os.makedirs(dest_dir_name, ROOT_READ_ONLY)


class SaferFileMove(object):
    """Try to copy a file avoiding race conditions.

    Opens the dest file os.O_RDWR | os.O_CREAT | os.O_EXCL, which
    guarantees that the file didn't exist before, that we created it,
    and that we are the only process that has it open. We also make sure
    the perms are so that only root can read the result.

    Then we copy the contents of the src file to the new dest file,
    and unlink the src file."""
    def __init__(self):
        # based on shutils copyfileob
        self.buf_size = 16 * 1024
        # only root can read
        self.default_perms = ROOT_READ_ONLY

    def move(self, src, dest):
        """Move a file to a dest dir, potentially /tmp more safely.

        If dest is /tmp, or a specific name in /tmp, we want to
        create it excl if we can."""
        try:
            src_fo = open(src, 'r')
            # if dest doesn't exist, and we can open it excl, then open it,
            # keep the fd, create a file object for it, and write to it
            try:
                dest_fo = self._open_excl(dest)
                self._copyfileobj(src_fo, dest_fo)
            finally:
                dest_fo.close()
        finally:
            src_fo.close()

        os.unlink(src)

    def _open_excl(self, path):
        """Return a file object that we know we created and nothing else owns."""
        return os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL,
                                 self.default_perms), 'w+')

    def _copyfileobj(self, src_fo, dest_fo):
        while 1:
            buf = src_fo.read(self.buf_size)
            if not buf:
                break
            dest_fo.write(buf)
