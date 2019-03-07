from __future__ import print_function, division, absolute_import

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
import optparse
import os
import sys
import shutil
import logging
import tarfile
from datetime import datetime
from shutil import ignore_patterns

import subscription_manager.injection as inj
import subscription_manager.managercli as managercli
from subscription_manager.managercli import CliCommand
from subscription_manager.cli import InvalidCLIOptionError, system_exit
from subscription_manager.certdirectory import DEFAULT_PRODUCT_CERT_DIR
from rhsm import ourjson as json
from rhsm.config import initConfig
from rhsmlib.services import config

from subscription_manager.i18n import ugettext as _

log = logging.getLogger('rhsm-app.' + __name__)

conf = config.Config(initConfig())

ERR_NOT_REGISTERED_MSG = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")
ERR_NOT_REGISTERED_CODE = 1

ASSEMBLE_DIR = '/var/spool/rhsm/debug'
ROOT_READ_ONLY_DIR = 0o700
ROOT_READ_ONLY_FILE = 0o600
KEY_IGNORE_PATS = ['*key.pem']


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
        # These options don't do anything anymore, since current versions of
        # RHSM api doesn't support it, and previously they failed silently.
        # So now they are hidden, and they are not hooked up to anything. This
        # avoids breaking existing scripts, since it also didn't do anything
        # before. See rhbz #1246680
        self.parser.add_option("--no-subscriptions", action='store_true',
                               dest="placeholder_for_subscriptions_option",
                               default=False, help=optparse.SUPPRESS_HELP)
        self.parser.add_option("--subscriptions", action='store_true',
                               dest="placeholder_for_subscriptions_option",
                               default=False, help=optparse.SUPPRESS_HELP)

        self.assemble_path = ASSEMBLE_DIR

        # so we can track the path of the archive for tests.
        self.final_destination_path = None

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] ") % self.name

    def _validate_options(self):
        if self.options.destination and not os.path.exists(self.options.destination):
            raise InvalidCLIOptionError(_("The directory specified by '--destination' must already exist."))
        # no archive, check if we can safely copy to dest.
        if not self.options.archive:
            if not self._dirs_on_same_device(self.assemble_path, self.options.destination):
                msg = _("To use the no-archive option, the destination directory '%s' "
                        "must exist on the same file system as the "
                        "data assembly directory '%s'.") % (self.options.destination, self.assemble_path)
                raise InvalidCLIOptionError(msg)
        # In case folks are using this in a script
        if self.options.placeholder_for_subscriptions_option:
            log.debug("The rhsm-debug options '--subscriptions' and '--no-subscriptions' have no effect now.")

    def _dirs_on_same_device(self, dir1, dir2):
        return os.stat(dir1).st_dev == os.stat(dir2).st_dev

    def _do_command(self):
        self.options.destination = os.path.expanduser(self.options.destination)
        self._validate_options()
        consumer = inj.require(inj.IDENTITY)
        if not consumer.is_valid():
            system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)

        code = self._make_code()
        archive_name = "rhsm-debug-system-%s" % code
        tar_file_name = "%s.tar.gz" % archive_name
        # /var/spool/rhsm/debug/rhsm-debug-system-20131212-121234/
        content_path = os.path.join(self.assemble_path, archive_name)
        # /var/spool/rhsm/debug/rhsm-debug-system-20131212-123413.tar.gz
        tar_file_path = os.path.join(self.assemble_path, tar_file_name)

        try:
            # assemble path is in the package, so should always exist
            self._makedir(content_path)

            owner = self.cp.getOwner(consumer.uuid)

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
            defaults = conf.defaults()
            # sosreport collects /etc/rhsm/* and /var/*/rhsm/*, so these would
            # be redundant for sos
            if not sos:
                # copy rhsm.conf specifically
                self._copy_cert_directory("/etc/rhsm", content_path)
                self._copy_directory('/var/log/rhsm', content_path)
                self._copy_directory('/var/lib/rhsm', content_path)

            if not sos:
                self._copy_cert_directory(DEFAULT_PRODUCT_CERT_DIR, content_path)

            if defaults['productcertdir'] != conf['rhsm']['productCertDir'] or not sos:
                self._copy_cert_directory(conf['rhsm']['productCertDir'], content_path)

            if defaults['entitlementcertdir'] != conf['rhsm']['entitlementCertDir'] or not sos:
                self._copy_cert_directory(conf['rhsm']['entitlementCertDir'], content_path)

            if defaults['consumercertdir'] != conf['rhsm']['consumerCertDir'] or not sos:
                self._copy_cert_directory(conf['rhsm']['consumerCertDir'], content_path)

            # If ca_cert_dir and pluginconfdif are configured as subdirs of /etc/rhsm
            # (as is the default) we will have already copied there contents,
            # so ignore directory exists errors
            try:
                if defaults['ca_cert_dir'] != conf['rhsm']['ca_cert_dir'] or not sos:
                    self._copy_cert_directory(conf['rhsm']['ca_cert_dir'], content_path)
            except EnvironmentError as e:
                if e.errno != errno.EEXIST:
                    raise

            try:
                if defaults['pluginconfdir'] != conf['rhsm']['pluginconfdir'] or not sos:
                    self._copy_directory(conf['rhsm']['pluginconfdir'], content_path)
            except EnvironmentError as e:
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

                self.final_destination_path = final_path

                sfm = SaferFileMove()
                sfm.move(tar_file_path, final_path)
                print(_("Wrote: %s") % final_path)
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

                print(_("Wrote: %s") % dest_dir_name)

        except Exception as e:
            managercli.handle_exception(_("Unable to create zip file of system information: %s") % e, e)
            sys.exit(os.EX_SOFTWARE)
        finally:
            if content_path and os.path.isdir(content_path):
                shutil.rmtree(content_path, True)

    def _make_code(self):
        return datetime.now().strftime("%Y%m%d-%f")

    def _get_version_info(self):
        return {"server type": self.server_versions["server-type"],
                "subscription management server": self.server_versions["candlepin"],
                "subscription-manager": self.client_versions["subscription-manager"]}

    def _write_flat_file(self, content_path, filename, content):
        path = os.path.join(content_path, filename)
        with open(path, "w+") as fo:
            fo.write(json.dumps(content, indent=4, sort_keys=True, default=json.encode))

    def _copy_directory(self, src_path, dest_path, ignore_pats=[]):
        rel_path = src_path
        if os.path.isabs(src_path):
            rel_path = src_path[1:]
        if ignore_pats is not None:
            shutil.copytree(src_path, os.path.join(dest_path, rel_path),
                ignore=ignore_patterns(*ignore_pats))
        else:
            shutil.copytree(src_path, os.path.join(dest_path, rel_path))

    def _copy_cert_directory(self, src_path, dest_path):
        self._copy_directory(src_path,
                             dest_path,
                             KEY_IGNORE_PATS)

    def _makedir(self, dest_dir_name):
        os.makedirs(dest_dir_name, ROOT_READ_ONLY_DIR)


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
        self.default_perms = ROOT_READ_ONLY_FILE

    def move(self, src, dest):
        """Move a file to a dest dir, potentially /tmp more safely.

        If dest is /tmp, or a specific name in /tmp, we want to
        create it excl if we can."""
        with open(src, 'rb') as src_fo:
            # if dest doesn't exist, and we can open it excl, then open it,
            # keep the fd, create a file object for it, and write to it
            with self._open_excl(dest) as dest_fo:
                self._copyfileobj(src_fo, dest_fo)

        os.unlink(src)

    def _open_excl(self, path):
        """Return a file object that we know we created and nothing else owns."""
        return os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL,
                                 self.default_perms), 'wb+')

    def _copyfileobj(self, src_fo, dest_fo):
        while True:
            buf = src_fo.read(self.buf_size)
            if not buf:
                break
            dest_fo.write(buf)
