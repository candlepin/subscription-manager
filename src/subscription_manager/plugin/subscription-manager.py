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
from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE

sys.path.append('/usr/share/rhsm')
from subscription_manager import logutil
from subscription_manager.repolib import RepoLib, EntitlementDirectory

requires_api_version = '2.5'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)


warning = \
"""
*** WARNING ***
The subscription for following product(s) has expired:
%s
You no longer have access to the repsoitories that
provide these products.  It is important that you renew
these subscriptions immediatly to resume access to security
and other critical updates.
"""


def update(conduit):
    """ update entitlement certificates """
    if os.getuid() != 0:
        conduit.info(2, 'Not root, Red Hat repositories not updated')
        return
    conduit.info(2, 'Updating Red Hat repositories.')
    rl = RepoLib()
    rl.update()


def warnExpired(conduit):
    """ display warning for expired entitlements """
    entdir = EntitlementDirectory()
    products = set()
    for cert in entdir.listExpired():
        for p in cert.getProducts():
            m = '  - %s' % p.getName()
            products.add(m)
    if products:
        msg = warning % '\n'.join(sorted(products))
        conduit.info(2, msg)


def config_hook(conduit):
    """ update """
    # register rpm name for yum history recording"
    # yum on 5.7 doesn't have this method, so check for it
    if hasattr(conduit, 'registerPackageName'):
        conduit.registerPackageName("subscription-manager")
    logutil.init_logger_for_yum()
    try:
        update(conduit)
        warnExpired(conduit)
    except Exception, e:
        conduit.error(2, str(e))
