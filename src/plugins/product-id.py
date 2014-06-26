#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

sys.path.append('/usr/share/rhsm')


from subscription_manager import logutil
from subscription_manager.productid import ProductManager
from subscription_manager.utils import chroot

requires_api_version = '2.6'
plugin_type = (TYPE_CORE,)


def posttrans_hook(conduit):
    """
    Update product ID certificates.
    """
    # register rpm name for yum history recording
    # yum on 5.7 doesn't have this method, so check for it
    if hasattr(conduit, 'registerPackageName'):
        conduit.registerPackageName("subscription-manager")

    try:
        from subscription_manager.injectioninit import init_dep_injection
        init_dep_injection()
    except ImportError, e:
        conduit.error(3, str(e))
        return

    logutil.init_logger_for_yum()
    # If a tool (it's, e.g., Anaconda and Mock) manages a chroot via
    # 'yum --installroot', we must update certificates in that directory.
    chroot(conduit.getConf().installroot)
    try:
        pm = ProductManager()
        pm.update(conduit._base)
        conduit.info(3, 'Installed products updated.')
    except Exception, e:
        conduit.error(3, str(e))
