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
        return "[PRODUCTNAME...]"

    def getSummary(self):
        return _("Removes all packages related to a particular product")

    def doCheck(self, base, basecmd, extcmds):
        pass

    def doCommand(self, base, basecmd, extcmds):
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

        for product in extcmds:
            for ipkg in sorted(pkgs):
                if 'from_repo' in ipkg.yumdb_info and ipkg.yumdb_info.from_repo in product_repo_mapping.get(product):
                    # add the package to the erasure transaction
                    base.remove(ipkg)

        if len(base.tsInfo) == 0:
            return 0, [_("No packages found for selected products")]

        if base.doTransaction() == 0:
            return 0, [_("Removed packages for selected products")]
        else:
            return 0, [_("Error occured while removing packages. Please see yum.log for more details.")]


def config_hook(conduit):
    parser = conduit.getOptParser()
    if not parser:
        return

    if hasattr(parser, 'plugin_option_group'):
        parser = parser.plugin_option_group

    conduit.registerCommand(EraseProductCommand())
