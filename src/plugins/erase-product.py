#
# Copyright (c) 2012 Red Hat, Inc.
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

import sys
from yum.plugins import TYPE_CORE
sys.path.append("/usr/share/rhsm")
from subscription_manager.productid import ProductDatabase
from subscription_manager.certdirectory import ProductDirectory

requires_api_version = '2.6'
plugin_type = (TYPE_CORE,)

repofiles = {}

YUM_REPO_DIR = '/etc/yum.repos.d/'


class EraseProductCommand:

    def getNames(self):
        return ['erase-product']

    def getUsage(self):
        return "usage info here"

    def getSummary(self):
        return "Removes all packages related to a particular product"

    def doCheck(self, base, basecmd, extcmds):
        pass

    def doCommand(self, base, basecmd, extcmds):
        opts = base.plugins.cmdline[0]
        pkgs = base.rpmdb
        product_dir = ProductDirectory()
        product = {}
        for p in product_dir.list():
            for p in p.products:
                product[p.id] = p.name

        product_db = ProductDatabase()
        product_db.read()
        # convert IDs to names in the mapping
        product_repo_mapping = dict((product[k], v) for k, v in product_db.content.iteritems())

        for ipkg in sorted(pkgs):
            if 'from_repo' in ipkg.yumdb_info and ipkg.yumdb_info.from_repo == product_repo_mapping.get(opts.product_name):
                # add the package to the erasure queue
                base.remove(ipkg)

        if len(base.tsInfo) == 0:
            return 0, ["No packages found for product %s" % opts.product_name]

        if base.doTransaction() == 0:
            return 0, ["Removed packages for %s" % opts.product_name]
        else:
            return 0, ["Error occured while removing packages for %s. Please see yum.log for more details." % opts.product_name]


def config_hook(conduit):
    parser = conduit.getOptParser()
    if not parser:
        return

    if hasattr(parser, 'plugin_option_group'):
        parser = parser.plugin_option_group

    conduit.registerCommand(EraseProductCommand())

    parser.add_option('--productname', action="store", dest='product_name',
                      help='Remove packages for a particular product')
