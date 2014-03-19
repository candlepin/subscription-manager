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

from subscription_manager import injection as inj
from subscription_manager.repolib import RepoLib
from rhsm import connection
from rhsm import config

requires_api_version = '2.5'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)

# TODO: translate strings

expired_warning = \
"""
*** WARNING ***
The subscription for following product(s) has expired:
%s
You no longer have access to the repositories that provide these products.  It is important that you apply an active subscription in order to resume access to security and other critical updates. If you don't have other active subscriptions, you can renew the expired subscription.  """

not_registered_warning = \
"This system is not registered to Red Hat Subscription Management. You can use subscription-manager to register."

no_subs_warning = \
"This system is registered to Red Hat Subscription Management, but is not receiving updates. You can use subscription-manager to assign subscriptions."


def update(conduit, cache_only):
    """ update entitlement certificates """
    if os.getuid() != 0:
        conduit.info(3, 'Not root, Subscription Management repositories not updated')
        return
    conduit.info(3, 'Updating Subscription Management repositories.')

    # XXX: Importing inline as you must be root to read the config file
    from subscription_manager.identity import ConsumerIdentity

    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()

    identity = inj.require(inj.IDENTITY)

    if not identity.is_valid():
        conduit.info(3, "Unable to read consumer identity")
        return

    try:
        uep = connection.UEPConnection(cert_file=cert_file, key_file=key_file)
    #FIXME: catchall exception
    except Exception:
        # log
        conduit.info(2, "Unable to connect to Subscription Management Service")
        return

    rl = RepoLib(uep=uep, cache_only=cache_only)
    rl.update()


def warnExpired(conduit):
    """ display warning for expired entitlements """
    entdir = inj.require(inj.ENT_DIR)
    products = set()
    for cert in entdir.list_expired():
        for p in cert.products:
            m = '  - %s' % p.name
            products.add(m)
    if products:
        msg = expired_warning % '\n'.join(sorted(products))
        conduit.info(2, msg)


def warnOrGiveUsageMessage(conduit):

    # XXX: Importing inline as you must be root to read the config file

    """ either output a warning, or a usage message """
    msg = ""
    # TODO: refactor so there are not two checks for this
    if os.getuid() != 0:
        return
    try:
        identity = inj.require(inj.IDENTITY)
        if not identity.is_valid():
            msg = not_registered_warning

        entdir = inj.require(inj.ENT_DIR)
        if len(entdir.list_valid()) == 0:
            msg = no_subs_warning

    finally:
        if msg:
            conduit.info(2, msg)


def config_hook(conduit):
    """ update """
    # register rpm name for yum history recording"
    # yum on 5.7 doesn't have this method, so check for it

    from subscription_manager import logutil
    logutil.init_logger_for_yum()

    from subscription_manager.injectioninit import init_dep_injection
    init_dep_injection()

    cfg = config.initConfig()
    cache_only = not bool(cfg.get_int('rhsm', 'full_refresh_on_yum'))

    if hasattr(conduit, 'registerPackageName'):
        conduit.registerPackageName("subscription-manager")
    try:
        update(conduit, cache_only)
        warnOrGiveUsageMessage(conduit)
        warnExpired(conduit)
    except Exception, e:
        conduit.error(2, str(e))
