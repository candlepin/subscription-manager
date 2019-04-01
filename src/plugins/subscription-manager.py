from __future__ import print_function, division, absolute_import

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
from yum.plugins import TYPE_CORE

from subscription_manager import injection as inj
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.entcertlib import EntCertActionInvoker
from rhsmlib.facts.hwprobe import ClassicCheck
from subscription_manager.certlib import Locker
from subscription_manager.utils import chroot
from subscription_manager.injectioninit import init_dep_injection
from subscription_manager import logutil
from rhsm import connection
from rhsm import config

requires_api_version = '2.5'
plugin_type = (TYPE_CORE,)

# TODO: translate strings

expired_warning = """
*** WARNING ***
The subscription for following product(s) has expired:
%s
You no longer have access to the repositories that provide these products.  It is important that you apply an active subscription in order to resume access to security and other critical updates. If you don't have other active subscriptions, you can renew the expired subscription.
"""

not_registered_warning = """
This system is not registered with an entitlement server. You can use subscription-manager to register.
"""

no_subs_warning = """
This system is registered with an entitlement server, but is not receiving updates. You can use subscription-manager to assign subscriptions.
"""

no_subs_container_warning = """
This system is not receiving updates. You can use subscription-manager on the host to register and assign subscriptions.
"""


# If running from the yum plugin, we want to avoid blocking
# yum forever on locks created by other rhsm processes. We try
# to acquire the lock before potentially updating redhat.repo, but
# if we can't, the plugin will fail back to not updating it.
# So this class provides a Locker uses the default ACTION_LOCK,
# but if it would have to wait for it, it decides to do nothing
# instead.
class YumRepoLocker(Locker):
    def __init__(self, conduit):
        super(YumRepoLocker, self).__init__()
        self.conduit = conduit

    def run(self, action):
        # lock.acquire will return False if it would block
        # NOTE: acquire can return None, True, or False
        #       with different meanings.
        nonblocking = self.lock.acquire(blocking=False)
        if nonblocking is False:
            # Could try to grab the pid for the log message, but it's a bit of a race.
            self.conduit.info(3, "Another process has the cert lock. We will not attempt to update certs or repos.")
            return 0
        try:
            return action()
        finally:
            self.lock.release()


def update(conduit, cache_only):
    """
    Update entitlement certificates
    """
    if os.getuid() != 0:
        conduit.info(3, 'Not root, Subscription Management repositories not updated')
        return
    conduit.info(3, 'Updating Subscription Management repositories.')

    # XXX: Importing inline as you must be root to read the config file
    from subscription_manager.identity import ConsumerIdentity

    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()

    identity = inj.require(inj.IDENTITY)

    # In containers we have no identity, but we may have entitlements inherited
    # from the host, which need to generate a redhat.repo.
    if identity.is_valid():
        if not cache_only:
            try:
                connection.UEPConnection(cert_file=cert_file, key_file=key_file)
            except Exception:
                # log
                conduit.info(2, "Unable to connect to Subscription Management Service")
                return
    else:
        conduit.info(3, "Unable to read consumer identity")

    if config.in_container():
        conduit.info(3, "Subscription Manager is operating in container mode.")

    if not cache_only and not config.in_container():
        cert_action_invoker = EntCertActionInvoker(locker=YumRepoLocker(conduit=conduit))
        cert_action_invoker.update()

    repo_action_invoker = RepoActionInvoker(cache_only=cache_only, locker=YumRepoLocker(conduit=conduit))
    repo_action_invoker.update()


def warn_expired_entitlements(conduit):
    """
    When some entitlement is expired, then display warning message about it
    """
    ent_dir = inj.require(inj.ENT_DIR)
    products = set()

    for cert in ent_dir.list_expired():
        for product in cert.products:
            m = '  - %s' % product.name
            products.add(m)

    if products:
        msg = expired_warning % '\n'.join(sorted(products))
        conduit.info(2, msg)


def warn_or_usage_message(conduit):
    """
    Display warning message, when the system is not registered (no consumer cert) or then is no entitlement cert
    """

    if os.getuid() != 0:
        return
    if ClassicCheck().is_registered_with_classic():
        return

    msg = ""
    try:
        identity = inj.require(inj.IDENTITY)
        ent_dir = inj.require(inj.ENT_DIR)
        # Don't warn people to register if we see entitlements, but no identity:
        if not identity.is_valid() and len(ent_dir.list_valid()) == 0:
            msg = not_registered_warning
        elif len(ent_dir.list_valid()) == 0:
            # XXX: Importing inline as you must be root to read the config file
            from subscription_manager.identity import ConsumerIdentity

            cert_file = ConsumerIdentity.certpath()
            key_file = ConsumerIdentity.keypath()

            # In containers we have no identity, but we may have entitlements inherited
            # from the host, which need to generate a redhat.repo.
            if identity.is_valid():
                try:
                    uep = connection.UEPConnection(cert_file=cert_file, key_file=key_file)
                # FIXME: catchall exception
                except Exception:
                    pass
                else:
                    owner = uep.getOwner(identity.uuid)
                    if owner['contentAccessMode'] != "org_environment":
                        return

            msg = no_subs_warning
        if config.in_container() and len(ent_dir.list_valid()) == 0:
            msg = no_subs_container_warning
    finally:
        if msg:
            conduit.info(2, msg)


def init_hook(conduit):
    """
    Hook for disabling system repositories (repositories which are
    not mangaged by subscription-manager will NOT be used)
    """

    disable_system_repos = conduit.confBool('main', 'disable_system_repos', default=False)

    if disable_system_repos:
        disable_count = 0
        repo_storage = conduit.getRepos()
        for repo in repo_storage.repos.values():
            if os.path.basename(repo.repofile) != "redhat.repo" and repo.enabled is True:
                conduit.info(2, 'Disabling system repository "%s" in file "%s"' % (repo.id, repo.repofile))
                repo_storage.disableRepo(repo.id)
                disable_count += 1
        conduit.info(2, 'subscription-manager plugin disabled "%d" system repositories with respect of configuration in /etc/yum/pluginconf.d/subscription-manager.conf' % (disable_count))


def config_hook(conduit):
    """
    This is the first hook of this yum plugin that is triggered by yum. So we do initialization
    of all stuff that is necessary by other hooks
    :param conduit: Reference on conduit object used by yum plugin API
    :return: None
    """
    logutil.init_logger_for_yum()
    init_dep_injection()

    if hasattr(conduit, 'registerPackageName'):
        conduit.registerPackageName("subscription-manager")


def postconfig_hook(conduit):
    """
    Try to display some warning messages, when it is necessary.
    :param conduit: Reference on conduit object used by yum plugin API
    :return: None
    """

    # If a tool (it's, e.g., Mock) manages a chroot via 'yum --installroot',
    # we must update entitlements in that directory.
    # Note: conduit.getConf() is available in postconfig_hook
    chroot(conduit.getConf().installroot)

    # It is save to display following warning messages for all yum commands, because following functions
    # does not communicate with candlepin server. See: https://bugzilla.redhat.com/show_bug.cgi?id=1621275
    try:
        warn_or_usage_message(conduit)
        warn_expired_entitlements(conduit)
    except Exception as e:
        conduit.error(2, str(e))


def prereposetup_hook(conduit):
    """
    Try to update configuration of redhat.repo, before yum tries to load configuration of repositories.
    :param conduit: Reference on conduit object used by yum plugin API
    :return: None
    """

    cfg = config.initConfig()
    cache_only = not bool(cfg.get_int('rhsm', 'full_refresh_on_yum'))

    try:
        update(conduit, cache_only)
    except Exception as e:
        conduit.error(2, str(e))
