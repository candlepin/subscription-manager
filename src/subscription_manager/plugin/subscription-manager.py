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
from subscription_manager.hwprobe import ClassicCheck
from subscription_manager.repolib import RepoLib, EntitlementDirectory
from rhsm import connection

requires_api_version = '2.5'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)

# TODO: translate strings

expired_warning = \
"""
*** WARNING ***
The subscription for following product(s) has expired:
%s
You no longer have access to the repositories that
provide these products.  It is important that you apply an
active subscription in order to resume access to security
and other critical updates. If you don't have other active
subscriptions, you can renew the expired subscription.
"""

not_registered_warning = \
"This system is not registered to Red Hat Subscription Management. You can use subscription-manager to register."

registered_message = \
"This system is receiving updates from Red Hat Subscription Management."

no_subs_warning = \
"This system is registered to Red Hat Subscription Management, but not recieving updates. You can use subscription-manager to assign subscriptions."


def update(conduit):
    """ update entitlement certificates """
    if os.getuid() != 0:
        conduit.info(2, 'Not root, certificate-based repositories not updated')
        return
    conduit.info(2, 'Updating certificate-based repositories.')

    # XXX: Importing inline as you must be root to read the config file
    from subscription_manager.certlib import ConsumerIdentity

    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()

    try:
        ConsumerIdentity.read().getConsumerId()
    except Exception:
        conduit.error(2, "Unable to read consumer identity")
        return

    try:
        uep = connection.UEPConnection(cert_file=cert_file, key_file=key_file)
    #FIXME: catchall exception
    except Exception:
        # log
        conduit.info(2, "Unable to connect to entitlement server")
        return

    rl = RepoLib(uep=uep)
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
        msg = expired_warning % '\n'.join(sorted(products))
        conduit.info(2, msg)


def warnOrGiveUsageMessage(conduit):
    """ either output a warning, or a usage message """
    msg = ""
    # TODO: refactor so there are not two checks for this
    if os.getuid() != 0:
        return
    try:
        try:
            ConsumerIdentity.read().getConsumerId()
            entdir = EntitlementDirectory()
            if len(entdir.listValid()) == 0:
                msg = no_subs_warning
            else:
                msg = registered_message
        except:
            msg = not_registered_warning
    finally:
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
        if not ClassicCheck().is_registered_with_classic():
                warnOrGiveUsageMessage(conduit)
                warnExpired(conduit)
    except Exception, e:
        conduit.error(2, str(e))
