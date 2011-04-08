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

import os
import sys
from yum.plugins import TYPE_CORE

sys.path.append('/usr/share/rhsm')
from subscription_manager import logutil
from subscription_manager.productid import ProductManager
from subscription_manager.certlib import Path

requires_api_version = '2.6'
plugin_type = (TYPE_CORE,)


def chroot():
    """
    Use /mnt/sysimage when it exists to support operating
    within an Anaconda installation.
    """
    sysimage = '/mnt/sysimage'
    if os.path.exists(sysimage):
        Path.ROOT = sysimage


def postverifytrans_hook(conduit):
    """
    Update product ID certificates.
    """
    # register rpm name for yum history recording"
    conduit.registerPackageName("subscription-manager")
    logutil.init_logger_for_yum()
    chroot()
    try:
        pm = ProductManager()
        pm.update(conduit._base)
        conduit.error(2, 'Installed products updated.')
    except Exception, e:
        conduit.error(2, str(e))
