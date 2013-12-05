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

import gettext
import os
import sys
import tempfile
import shutil
import logging
import json
import subscription_manager.injection as inj
import subscription_manager.managercli as managercli

from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from subscription_manager.managercli import CliCommand

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

NOT_REGISTERED = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")


class SystemCommand(CliCommand):

    def __init__(self, name="system",
                 shortdesc=_("Create zip file with complete system information"),
                 primary=True):
        CliCommand.__init__(self, name=name, shortdesc=shortdesc, primary=primary)

        self.parser.add_option("--destination", dest="destination",
                               help=_("the destination location of the zip file"))

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] ") % self.name

    def _do_command(self):
        consumer = inj.require(inj.IDENTITY)
        if not consumer.is_valid():
            print (NOT_REGISTERED)
            sys.exit(-1)
        tmp_zip_path = ""
        tmp_flat_path = ""

        try:
            tmp_flat_path = tempfile.mkdtemp()
            self._write_flat_file(tmp_flat_path, "consumer.json",
                                  self.cp.getConsumer(consumer.uuid))
            self._write_flat_file(tmp_flat_path, "compliance.json",
                                  self.cp.getCompliance(consumer.uuid))
            self._write_flat_file(tmp_flat_path, "entitlements.json",
                                  self.cp.getEntitlementList(consumer.uuid))
            owner = self.cp.getOwner(consumer.uuid)
            self._write_flat_file(tmp_flat_path, "pools.json",
                                  self.cp.getPoolsList(consumer.uuid, True, None, owner['key']))
            try:
                self._write_flat_file(tmp_flat_path, "subscriptions.json",
                                      self.cp.getSubscriptionList(owner['key']))
            except Exception, e:
                log.warning("Server does not allow retrieval of subscriptions by owner.")
            self._write_flat_file(tmp_flat_path, "version.json",
                                  self._get_version_info())

            tmp_zip_path = tempfile.mkdtemp()
            zip_path = os.path.join(tmp_zip_path, "tmp-system.zip")
            zf = ZipFile(zip_path, "w", ZIP_DEFLATED)

            for filename in os.listdir(tmp_flat_path):
                zf.write(os.path.join(tmp_flat_path, filename), filename)
            zf.write('/etc/rhsm/rhsm.conf')
            self._dir_to_zip('/var/log/rhsm', zf)
            self._dir_to_zip('/var/lib/rhsm', zf)
            self._dir_to_zip('/etc/pki/product', zf)
            self._dir_to_zip('/etc/pki/entitlement', zf)
            self._dir_to_zip('/etc/pki/consumer', zf)
            zf.close()

            # move to final destination
            destination = '/tmp'
            if self.options.destination:
                destination = self.options.destination
                if not os.path.exists(destination):
                    os.makedirs(destination)
            final_zip_path = os.path.join(destination, "system-debug-%s.zip" % self._make_code())
            shutil.move(zip_path, final_zip_path)

            print _("Wrote: %s") % final_zip_path
        except Exception, e:
            managercli.handle_exception(_("Unable to create zip file of system information: %s") % e, e)
            sys.exit(-1)
        finally:
            shutil.rmtree(tmp_zip_path, True)
            shutil.rmtree(tmp_flat_path, True)

    def _dir_to_zip(self, directory, zipfile):
        for dirname, subdirs, files in os.walk(directory):
            zipfile.write(dirname)
            for filename in files:
                zipfile.write(os.path.join(dirname, filename))

    def _make_code(self):
        return datetime.now().strftime("%Y%m%d-%f")

    def _get_version_info(self):
        return [("server type: %s") % self.server_versions["server-type"],
                ("subscription management server: %s") % self.server_versions["candlepin"],
                ("subscription-manager: %s") % self.client_versions["subscription-manager"],
                ("python-rhsm: %s") % self.client_versions["python-rhsm"]]

    def _write_flat_file(self, path, filename, content):
        path = os.path.join(path, filename)
        try:
            with open(path, "a+") as fo:
                fo.write(str(json.dumps(content, indent=4, sort_keys=True)))
        finally:
            fo.close()
