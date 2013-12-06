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
import subscription_manager.injection as inj
import subscription_manager.managercli as managercli

from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from subscription_manager.managercli import CliCommand

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

NOT_REGISTERED = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")


class SystemCommand(CliCommand):

    def __init__(self, name="system", shortdesc=None, primary=False):
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
        consumerid = consumer.uuid
        path = tempfile.mkdtemp()

        try:
            original_path = os.getcwd()
            if not os.path.exists(path):
                os.makedirs(path)
            self._write_flat_file(path, "consumer.json", self.cp.getConsumer(consumerid))
            self._write_flat_file(path, "compliance.json", self.cp.getCompliance(consumerid))
            self._write_flat_file(path, "entitlements.json", self.cp.getEntitlementList(consumerid))
            owner = self.cp.getOwner(consumerid)
            self._write_flat_file(path, "pools.json", self.cp.getPoolsList(consumerid, True, None, owner['key']))

            try:
                self._write_flat_file(path, "subscriptions.json", self.cp.getSubscriptionList(owner['key']))
            except Exception, e:
                log.warning("Server does not allow retrieval of subscriptions by owner.")

            destination = '/tmp'
            if self.options.destination:
                destination = self.options.destination
            if not os.path.exists(destination):
                os.makedirs(destination)
            zippath = os.path.join(destination, "system-debug-%s.zip" % self._make_code())
            zf = ZipFile(zippath, "w", ZIP_DEFLATED)
            os.chdir(path)
            for filename in os.listdir(path):
                zf.write(filename)
            zf.write('/etc/rhsm/rhsm.conf')
            self._dir_to_zip('/var/log/rhsm', zf)
            self._dir_to_zip('/etc/pki/product', zf)
            self._dir_to_zip('/etc/pki/entitlement', zf)
            self._dir_to_zip('/etc/pki/consumer', zf)
            zf.close()
            shutil.rmtree(path)
        except Exception, e:
            managercli.handle_exception(_("Unable to create zip file of consumer information: %s") % e, e)
            sys.exit(-1)
        finally:
            os.chdir(original_path)

    def _dir_to_zip(self, directory, zipfile):
        for dirname, subdirs, files in os.walk(directory):
            zipfile.write(dirname)
            for filename in files:
                zipfile.write(os.path.join(dirname, filename))

    def _make_code(self):
        codelist = []
        now = str(datetime.now())
        date = str.split(now, " ")[0]
        datelist = str.split(date, "-")
        milli = str.split(now, ".")[1]

        codelist.append(datelist[0])
        codelist.append(datelist[1])
        codelist.append(datelist[2])
        codelist.append("-")
        codelist.append(milli)
        return ''.join(codelist)

    def _write_flat_file(self, path, filename, content):
        path = os.path.join(path, filename)
        fo = open(path, "w+")
        try:
            fo.write(str(content))
        finally:
            fo.close()
