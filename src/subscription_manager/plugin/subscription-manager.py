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
import ConfigParser

sys.path.append('/usr/share/rhsm')
from subscription_manager import logutil
from subscription_manager.hwprobe import ClassicCheck
from subscription_manager.repolib import RepoLib, EntitlementDirectory
from rhsm import connection

requires_api_version = '2.5'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)

# this fails as non root
# FIXME: this fais as non root
try:
    from subscription_manager.certlib import ConsumerIdentity
except ImportError:
    ConsumerIdentity = None
except ConfigParser.NoOptionError:
    ConsumerIdentity = None

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
"""
This machine has not been registered and therefore has
no access to security and other critical updates. Please
register using subscription-manager.
"""

repo_usage_message = \
"""
Please use yum-config-manager to configure which software
repositories are used with Red Hat Subscription Management.
"""

no_subs_warning = \
"""
This system has been registered to Red Hat Subscription
Management, but has no subscriptions applied. Please use
subscription-manager in order to enable access to security
and other critical updates.
"""


def update(conduit):
    """ update entitlement certificates """
    if os.getuid() != 0:
        conduit.info(2, 'Not root, certificate-based repositories not updated')
        return
    conduit.info(2, 'Updating certificate-based repositories.')

    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()

    try:
        ConsumerIdentity.read().getConsumerId()
    except Exception, e:
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
                msg = repo_usage_message
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
