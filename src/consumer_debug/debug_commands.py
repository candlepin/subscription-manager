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
import subscription_manager.injection as inj
import subscription_manager.managercli as managercli

from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from subscription_manager.managercli import CliCommand

_ = gettext.gettext

NOT_REGISTERED = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")

class CompileCommand(CliCommand):

    def __init__(self, name="compile", shortdesc=None, primary=False):
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
            if not os.path.exists(path):
                os.makedirs(path)
            self.write_flat_file(path, "consumer.json", self.cp.getConsumer(consumerid))
            self.write_flat_file(path, "compliance.json", self.cp.getCompliance(consumerid))
            self.write_flat_file(path, "entitlements.json", self.cp.getEntitlementList(consumerid))
            owner = self.cp.getOwner(consumerid)
            self.write_flat_file(path, "pools.json", self.cp.getPoolsList(consumerid, \
                True, None, owner['key']))
            self.write_flat_file(path, "subscriptions.json", self.cp.getSubscriptionList(owner['key']))

            destination = '/tmp'
            if self.options.destination:
                destination = self.options.destination
            if not os.path.exists(destination):
                os.makedirs(destination)
            zippath = os.path.join(destination, "consumer-debug-%s.zip" % self.make_code())
            zf = ZipFile(zippath, "w", ZIP_DEFLATED)
            original_path = os.getcwd()
            os.chdir(path)
            for filename in os.listdir(path):
                zf.write(filename)
            zf.write('/etc/rhsm/rhsm.conf')
            self.dir_to_zip('/var/log/rhsm', zf)
            self.dir_to_zip('/etc/pki/product', zf)
            self.dir_to_zip('/etc/pki/entitlement', zf)
            self.dir_to_zip('/etc/pki/consumer', zf)
            zf.close()
            shutil.rmtree(path)
        except Exception, e:
            managercli.handle_exception(_("Unable to create zip file of consumer information: %s") % e, e)
            sys.exit(-1)
        finally:
            os.chdir(original_path)

    def dir_to_zip(self, directory, zipfile):
        for dirname, subdirs, files in os.walk(directory):
            zipfile.write(dirname)
            for filename in files:
                zipfile.write(os.path.join(dirname, filename))

    def make_code(self):
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

    def write_flat_file(self, path, filename, content):
        path = os.path.join(path, filename)
        fo = open(path, "w+")
        try:
            fo.write(str(content))
        finally:
            fo.close()
