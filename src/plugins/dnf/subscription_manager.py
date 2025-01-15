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
import logging
import shutil
import signal

from subscription_manager import injection as inj
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.entcertlib import EntCertActionInvoker
from rhsmlib.facts.hwprobe import ClassicCheck
from subscription_manager.utils import chroot, is_simple_content_access, is_process_running
from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import ungettext, ugettext as _
from rhsm import logutil
from rhsm import config
from rhsm.utils import LiveStatusMessage
from rhsm.connection import RemoteServerException

from dnfpluginscore import logger
import dnf

from configparser import ConfigParser

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from subscription_manager.certdirectory import EntitlementDirectory
    from subscription_manager.identity import Identity
    from subscription_manager.cache import ReleaseStatusCache


expired_warning = _(
    """
*** WARNING ***
The subscription for following product(s) has expired:
%s
You no longer have access to the repositories that provide these products.  \
It is important that you apply an active subscription in order to resume access \
to security and other critical updates. If you don't have other active \
subscriptions, you can renew the expired subscription.  """
)

not_registered_warning = _(
    """
This system is not registered with an entitlement server. You can use subscription-manager to register.
"""
)

not_registered_warning_rhc = _(
    """
This system is not registered with an entitlement server. \
You can use "rhc" or "subscription-manager" to register.
"""
)

no_subs_warning = _(
    """
This system is registered with an entitlement server, but is not receiving updates. You can use \
subscription-manager to assign subscriptions.
"""
)

release_lock_warning = _(
    """
This system has release set to {release_version} and it receives updates only for this release.
"""
)

log = logging.getLogger("rhsm-app." + __name__)


class SubscriptionManager(dnf.Plugin):
    name = "subscription-manager"

    def __init__(self, base, cli):
        super(SubscriptionManager, self).__init__(base, cli)
        self.base = base
        self.cli = cli
        self._config()

    def _config(self):
        """update"""
        logutil.init_logger_for_yum()

        init_dep_injection()

        chroot(self.base.conf.installroot)

        cfg = config.get_config_parser()
        cache_only = not bool(cfg.get_int("rhsm", "full_refresh_on_yum"))

        try:
            if os.getuid() == 0:
                # Try to update entitlement certificates and redhat.repo file
                self._update(cache_only)
                if not config.in_container():
                    self._warn_or_give_usage_message()
            else:
                logger.info(_("Not root, Subscription Management repositories not updated"))
            self._warn_expired()
        except Exception as e:
            log.error(str(e))

    def config(self):
        """
        Read other configuration options (not enabled) from configuration file of this plugin
        """
        super(SubscriptionManager, self).config()
        config_path = self.base.conf.pluginconfpath[0]

        default_config_file = os.path.join(config_path, self.name + ".conf")

        if os.path.isfile(default_config_file):
            plugin_config = ConfigParser()
            plugin_config.read(default_config_file)

            if plugin_config.has_option("main", "disable_system_repos"):
                disable_system_repos = plugin_config.get("main", "disable_system_repos")
                if disable_system_repos == "1":
                    disable_count = 0
                    for repo in self.base.repos.iter_enabled():
                        if os.path.basename(repo.repofile) != "redhat.repo":
                            repo.disable()
                            disable_count += 1
                    logger.info(
                        ungettext(
                            "subscription-manager plugin disabled %d system repository with respect "
                            "of configuration in /etc/dnf/plugins/subscription-manager.conf",
                            "subscription-manager plugin disabled %d system repositories with respect "
                            "of configuration in /etc/dnf/plugins/subscription-manager.conf",
                            disable_count,
                        )
                        % disable_count
                    )
        else:
            logger.debug("Configuration file %s does not exist." % default_config_file)

    @staticmethod
    def _update(cache_only):
        """
        Update entitlement certificates and redhat.repo
        :param cache_only: is True, when rhsm.full_refresh_on_yum is set to 0 in rhsm.conf
        """

        logger.info(_("Updating Subscription Management repositories."))
        identity: Identity = inj.require(inj.IDENTITY)
        ent_dir: EntitlementDirectory = inj.require(inj.ENT_DIR)

        # During first phase of anonymous cloud registration the system has
        # valid entitlement certificates, but does not yet have any identity.
        # We have access to the content, so we shouldn't be reporting missing
        # identity certificate.
        if not config.in_container() and not identity.is_valid() and len(ent_dir.list_valid()) == 0:
            logger.info(_("Unable to read consumer identity"))

        if config.in_container():
            logger.info(_("subscription-manager is operating in container mode."))

        if cache_only is True:
            log.debug("DNF subscription-manager operates in cache-only mode")

        if not cache_only and not config.in_container():
            log.debug("Trying to update entitlement certificates and redhat.repo")
            cert_action_invoker = EntCertActionInvoker()
            cert_action_invoker.update()
        else:
            log.debug("Skipping updating of entitlement certificates")

        log.debug("Generating redhat.repo")
        repo_action_invoker = RepoActionInvoker(cache_only=cache_only)
        repo_action_invoker.update()

    @staticmethod
    def _warn_expired():
        """
        Display warning for expired entitlements
        """
        ent_dir = inj.require(inj.ENT_DIR)
        products = set()
        for cert in ent_dir.list_expired():
            for p in cert.products:
                m = "  - %s" % p.name
                products.add(m)
        if products:
            msg = expired_warning % "\n".join(sorted(products))
            logger.info(msg)

    @staticmethod
    def _warn_or_give_usage_message():
        """
        Either output a warning, or a usage message
        """
        msg = ""
        if ClassicCheck().is_registered_with_classic():
            return
        try:
            identity = inj.require(inj.IDENTITY)
            ent_dir = inj.require(inj.ENT_DIR)
            # Don't warn people to register if we see entitlements, but no identity:
            if not identity.is_valid() and len(ent_dir.list_valid()) == 0:
                if shutil.which("rhc") is not None:
                    msg = not_registered_warning_rhc
                else:
                    msg = not_registered_warning
            elif len(ent_dir.list_valid()) == 0 and not is_simple_content_access(identity=identity):
                msg = no_subs_warning
            else:
                # Try to read release version ONLY from cache document.
                # When cache document does not exist, then do not try to get this information
                # from candlepin server and slow down DNF plugin!
                release_cache: ReleaseStatusCache = inj.require(inj.RELEASE_STATUS_CACHE)
                release_version_dict: Optional[dict] = release_cache.read_cache_only()
                if release_version_dict:
                    try:
                        release_version: str = release_version_dict["releaseVer"]
                    except KeyError:
                        log.warning("The 'releaseVer' not included in the release version document")
                    else:
                        # Skip the case, when release does not exist at all, or it was unset
                        # and it is empty string
                        if release_version:
                            msg = release_lock_warning.format(release_version=release_version)
        finally:
            if msg:
                logger.info(msg)

    def transaction(self):
        """
        Call Package Profile
        """
        cfg = config.get_config_parser()
        if (
            cfg.get("rhsm", "report_package_profile") == "1"
            and cfg.get("rhsm", "package_profile_on_trans") == "1"
        ):
            log.debug("Uploading package profile")
            self._upload_profile()
        else:
            log.debug("Uploading package profile disabled in configuration file")

    def _upload_profile_blocking(self) -> None:
        """
        Try to upload DNF profile to server
        """
        log.debug("Uploading DNF profile in blocking mode")
        with LiveStatusMessage("Uploading DNF profile"):
            try:
                profile_mgr = inj.require(inj.PROFILE_MANAGER)
                identity = inj.require(inj.IDENTITY)
                profile_mgr.update_check(self.cp, identity.uuid)
            except RemoteServerException as err:
                # When it is not possible to upload profile ATM, then print only error about this
                # to rhsm.log. The rhsmcertd will try to upload it next time.
                log.error("Unable to upload profile: {err}".format(err=str(err)))

    def _upload_profile(self) -> None:
        """
        Try to upload DNF profile to server, when it is supported by server. This method
        tries to "outsource" this activity to rhsmcertd first. When it is not possible due to
        various reasons, then we try to do it ourselves in blocking way.
        """
        # First try to get PID of rhsmcertd from lock file
        try:
            with open("/var/lock/subsys/rhsmcertd", "r") as lock_file:
                rhsmcertd_pid = int(lock_file.readline())
        except (IOError, ValueError) as err:
            log.info(f"Unable to read rhsmcertd lock file: {err}")
        else:
            if is_process_running("rhsmcertd", rhsmcertd_pid) is True:
                # This will only send SIGUSR1 signal, which triggers gathering and uploading
                # of DNF profile by rhsmcertd. We try to "outsource" this activity to rhsmcertd
                # server to not block registration process
                log.debug(f"Sending SIGUSR1 signal to rhsmcertd process ({rhsmcertd_pid})")
                try:
                    os.kill(rhsmcertd_pid, signal.SIGUSR1)
                except OSError as err:
                    log.debug(f"Unable to send SIGUSR1 signal to rhsmcertd process: {err}")
                    self._upload_profile_blocking()
            else:
                log.info(f"rhsmcertd process with given PID: {rhsmcertd_pid} is not running")
                self._upload_profile_blocking()
