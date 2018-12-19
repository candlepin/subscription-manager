from __future__ import print_function, division, absolute_import

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

import os

from subscription_manager import injection as inj
from subscription_manager.action_client import ProfileActionClient
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.entcertlib import EntCertActionInvoker
from rhsmlib.facts.hwprobe import ClassicCheck
from subscription_manager.utils import chroot
from subscription_manager.injectioninit import init_dep_injection
from subscription_manager import logutil
from rhsm import connection
from rhsm import config

from dnfpluginscore import _, logger
import dnf

expired_warning = _("""
*** WARNING ***
The subscription for following product(s) has expired:
%s
You no longer have access to the repositories that provide these products.  It is important that you apply an active subscription in order to resume access to security and other critical updates. If you don't have other active subscriptions, you can renew the expired subscription.  """
)

not_registered_warning = _(
"This system is not registered to Red Hat Subscription Management. You can use subscription-manager to register."
)

no_subs_warning = _(
"This system is registered to Red Hat Subscription Management, but is not receiving updates. You can use subscription-manager to assign subscriptions."
)


class SubscriptionManager(dnf.Plugin):
    name = 'subscription-manager'

    def __init__(self, base, cli):
        super(SubscriptionManager, self).__init__(base, cli)
        self.base = base
        self.cli = cli
        self._config()

    def _config(self):
        """ update """
        logutil.init_logger_for_yum()

        init_dep_injection()

        chroot(self.base.conf.installroot)

        cfg = config.initConfig()
        cache_only = not bool(cfg.get_int('rhsm', 'full_refresh_on_yum'))

        try:
            if os.getuid() == 0:
                self._update(cache_only)
                self._warnOrGiveUsageMessage()
            else:
                logger.info(_('Not root, Subscription Management repositories not updated'))
            self._warnExpired()
        except Exception as e:
            logger.error(str(e))

    def _update(self, cache_only):
        """ update entitlement certificates """
        logger.info(_('Updating Subscription Management repositories.'))

        # XXX: Importing inline as you must be root to read the config file
        from subscription_manager.identity import ConsumerIdentity

        cert_file = str(ConsumerIdentity.certpath())
        key_file = str(ConsumerIdentity.keypath())

        identity = inj.require(inj.IDENTITY)

        # In containers we have no identity, but we may have entitlements inherited
        # from the host, which need to generate a redhat.repo.
        if identity.is_valid():
            try:
                connection.UEPConnection(cert_file=cert_file, key_file=key_file)
            # FIXME: catchall exception
            except Exception:
                # log
                logger.info(_("Unable to connect to Subscription Management Service"))
                return
        else:
            logger.info(_("Unable to read consumer identity"))

        if config.in_container():
            logger.info(_("Subscription Manager is operating in container mode."))

        if not cache_only and not config.in_container():
            cert_action_invoker = EntCertActionInvoker()
            cert_action_invoker.update()

        repo_action_invoker = RepoActionInvoker(cache_only=cache_only)
        repo_action_invoker.update()

    def _warnExpired(self):
        """ display warning for expired entitlements """
        ent_dir = inj.require(inj.ENT_DIR)
        products = set()
        for cert in ent_dir.list_expired():
            for p in cert.products:
                m = '  - %s' % p.name
                products.add(m)
        if products:
            msg = expired_warning % '\n'.join(sorted(products))
            logger.info(msg)

    def _warnOrGiveUsageMessage(self):
        """ either output a warning, or a usage message """
        msg = ""
        if ClassicCheck().is_registered_with_classic():
            return
        try:
            identity = inj.require(inj.IDENTITY)
            ent_dir = inj.require(inj.ENT_DIR)
            # Don't warn people to register if we see entitelements, but no identity:
            if not identity.is_valid() and len(ent_dir.list_valid()) == 0:
                msg = not_registered_warning
            elif len(ent_dir.list_valid()) == 0:
                msg = no_subs_warning

        finally:
            if msg:
                logger.info(msg)

    def transaction(self):
        """
        Call Package Profile
        """
        cfg = config.initConfig()
        if '1' == cfg.get('rhsm', 'package_profile_on_trans'):
            package_profile_client = ProfileActionClient()
            package_profile_client.update()
        else:
            # do nothing
            return
