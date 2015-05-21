#
# Copyright (c) 2015 Red Hat, Inc.
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

sys.path.append('/usr/share/rhsm')

from subscription_manager import logutil
from subscription_manager.productid import ProductManager, package_manager
from subscription_manager.utils import chroot
from subscription_manager.injectioninit import init_dep_injection

from dnfpluginscore import _, logger
import dnf

class ProductId(dnf.Plugin):
    name = 'product-id'

    def __init__(self, base, cli):
        super(ProductId, self).__init__(base, cli)
        self.base = base
        self.cli = cli

    def transaction(self):
        """
        Update product ID certificates.
        """
        if len(self.base.transaction) == 0:
            # nothing to update after empty transaction
            return

        try:
            init_dep_injection()
        except ImportError as e:
            logger.error(str(e))
            return

        logutil.init_logger_for_yum()
        chroot(self.base.conf.installroot)
        try:
            pm = ProductManager()
            pm.update(package_manager(self.base))
            logger.info(_('Installed products updated.'))
        except Exception as e:
            logger.error(str(e))
