# Copyright (c) 2012 Red Hat, Inc.
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
import base64
import enum
import logging
import random
import signal
import sys
import time
from argparse import SUPPRESS
from typing import Dict, List, Union, TYPE_CHECKING

from cloud_what.provider import detect_cloud_provider, CLOUD_PROVIDERS, BaseCloudProvider

from rhsm import connection, config, logutil

from rhsmlib.services.register import RegisterService

import subscription_manager.utils
import subscription_manager.injection as inj
from subscription_manager import cache
from subscription_manager import entcertlib
from subscription_manager import managerlib
from subscription_manager.action_client import HealingActionClient, ActionClient
from subscription_manager.i18n import ugettext as _
from subscription_manager.i18n_argparse import ArgumentParser, USAGE
from subscription_manager.identity import Identity, ConsumerIdentity
from subscription_manager.injectioninit import init_dep_injection


if TYPE_CHECKING:
    import argparse
    from rhsm.config import RhsmConfigParser
    from rhsm.connection import UEPConnection
    from subscription_manager.cp_provider import CPProvider


class ExitStatus(enum.IntEnum):
    """Well-known exit codes.

    WARNING: THIS IS NOT A PUBLIC API.
    Values of these errors should not be used by any external applications, they are subject
    to change at any time without warning.
    External applications should only differentiate between zero and non-zero exit codes.
    """

    OK = 0

    RHSMCERTD_DISABLED = 5
    """rhsmcertd has been disabled through the config file."""
    LOCAL_CORRUPTION = 6
    """Local data have been corrupted."""

    NO_CLOUD_PROVIDER = 10
    """No public cloud provider has been detected."""
    NO_CLOUD_METADATA = 11
    """Public cloud provider has been detected, but metadata could not be obtained."""

    NO_REGISTRATION_TOKEN = 20
    """Registration token could not be obtained: server or cache are unavailable or broken."""
    BAD_TOKEN_TYPE = 21
    """Registration token was received, but is not recognized."""

    REGISTRATION_FAILED = 30
    """The system registration was not successful."""

    UNKNOWN_ERROR = -1
    """An unknown error occurred."""


init_dep_injection()

log = logging.getLogger(f"rhsm-app.{__name__}")


def exit_on_signal(_signumber, _stackframe):
    sys.exit(ExitStatus.OK)


def _is_enabled() -> bool:
    """Check if rhsmcertd is enabled or disabled."""
    cfg: RhsmConfigParser = config.get_config_parser()
    if cfg.get("rhsmcertd", "disable") == "1":
        return False
    return True


def _is_registered() -> bool:
    """Check if the system is registered."""
    identity: Identity = inj.require(inj.IDENTITY)
    return identity.is_valid()


def _create_cp_provider() -> "CPProvider":
    """Create a CPProvider with unique correlation ID."""
    provider: CPProvider = inj.require(inj.CP_PROVIDER)
    provider.set_correlation_id(correlation_id=subscription_manager.utils.generate_correlation_id())
    log.debug(f"X-Correlation-ID: {provider.correlation_id}")
    return provider


def _collect_cloud_info(cloud_list: List[str]) -> dict:
    """
    Try to collect cloud information: metadata and signature provided by cloud provider.
    :param cloud_list: The list of detected cloud providers. In most cases the list contains only one item.
    :return:
        Dictionary with 'metadata' and 'signature' (if it is provided by cloud provider),
        both encoded in base64.
        Empty dictionary is returned if metadata cannot be collected.
    """
    log.debug(f"Collecting metadata from cloud provider(s): {cloud_list}")

    # Create dispatcher dictionary from the list of supported cloud providers
    cloud_providers = {provider_cls.CLOUD_PROVIDER_ID: provider_cls for provider_cls in CLOUD_PROVIDERS}

    result = {}
    # Go through the list of detected cloud providers and try to collect
    # metadata. When metadata are gathered, then break the loop
    for cloud_provider_id in cloud_list:
        # hw_info is set to {}, because we do not need to detect cloud providers
        cloud_provider: BaseCloudProvider = cloud_providers[cloud_provider_id](hw_info={})

        # Try to get metadata first
        metadata: Union[str, None] = cloud_provider.get_metadata()

        # When it wasn't possible to get metadata for this cloud provider, then
        # continue with next detected cloud provider
        if metadata is None:
            log.warning(f"No metadata gathered for cloud provider: {cloud_provider_id}")
            continue

        # Try to get signature
        signature: Union[str, None] = cloud_provider.get_signature()

        # When it is not possible to get signature for given cloud provider,
        # then silently set signature to empty string, because some cloud
        # providers does not provide signatures
        if signature is None:
            signature = ""

        log.info(f"Metadata and signature gathered for cloud provider: {cloud_provider_id}")

        result = {
            "cloud_id": cloud_provider_id,
            "metadata": base64.b64encode(bytes(metadata, "utf-8")).decode("ascii"),
            "signature": base64.b64encode(bytes(signature, "utf-8")).decode("ascii"),
        }
        break

    return result


def _auto_register(cp_provider: "CPProvider") -> ExitStatus:
    """Try to perform automatic registration.

    :param cp_provider: Provider of connection to Candlepin.
    :returns: ExitStatus describing the result of a registration otherwise.
    """
    log.info("Starting automatic registration.")

    log.debug("Detecting cloud provider.")
    # Try to detect cloud provider first. We use lower threshold in this case, not the
    # default, because we want to have more sensitive detection in this case;
    # automatic registration is more important than reporting of facts.
    cloud_list = detect_cloud_provider(threshold=0.3)
    if len(cloud_list) == 0:
        log.warning(
            "This system does not run on any supported cloud provider. "
            "Automatic registration cannot be performed."
        )
        return ExitStatus.NO_CLOUD_PROVIDER

    # When some cloud provider(s) were detected, then try to collect metadata and signature
    cloud_info = _collect_cloud_info(cloud_list)
    if len(cloud_info) == 0:
        log.warning("Cloud metadata could not be collected. Unable to perform automatic registration.")
        return ExitStatus.NO_CLOUD_METADATA

    # Get connection not using any authentication
    uep: UEPConnection = cp_provider.get_no_auth_cp()

    # Obtain automatic registration token
    try:
        token: Dict[str, str] = cache.CloudTokenCache._get_from_server(
            uep=uep,
            cloud_id=cloud_info["cloud_id"],
            metadata=cloud_info["metadata"],
            signature=cloud_info["signature"],
        )
    except Exception:
        log.exception("Cloud token could not be obtained. Unable to perform automatic registration.")
        return ExitStatus.NO_REGISTRATION_TOKEN

    try:
        _auto_register_standard(uep=uep, token=token)
    except Exception:
        log.exception("Standard automatic registration failed.")
        return ExitStatus.REGISTRATION_FAILED
    else:
        log.info("Standard automatic registration was successful.")
        return ExitStatus.OK


def _auto_register_standard(uep: "UEPConnection", token: Dict[str, str]) -> None:
    """Perform standard automatic registration.

    The service will download identity certificate and entitlement certificates.

    :raises Exception: The system could not be registered.
    """
    log.debug("Registering the system through standard automatic registration.")

    service = RegisterService(cp=uep)
    service.register(org=None, jwt_token=token)


def _auto_register_anonymous(uep: "UEPConnection", token: Dict[str, str]) -> None:
    """Perform anonymous automatic registration.

    First we download the anonymous entitlement certificates and install them.

    Then we wait the 'splay' period. This makes sure we give the cloud backend
    enough time to create all the various objects in the Candlepin database.

    Then we perform the registration to obtain identity certificate and proper
    entitlement certificates.

    :raises TimeoutError: JWT expired, the system could be registered.
    :raises Exception: The system could not be registered.
    """
    log.debug("Registering the system through anonymous automatic registration.")

    # Step 1: Get the anonymous entitlement certificates
    manager = entcertlib.AnonymousCertificateManager(uep=uep)
    manager.install_temporary_certificates(uuid=token["anonymousConsumerUuid"], jwt=token["token"])

    # Step 2: Wait
    cfg = config.get_config_parser()
    if cfg.get("rhsmcertd", "splay") == "0":
        log.debug("Trying to obtain the identity immediately, splay is disabled.")
    else:
        registration_interval = int(cfg.get("rhsmcertd", "auto_registration_interval"))
        splay_interval: int = random.randint(60, registration_interval * 60)
        log.debug(
            f"Waiting a period of {splay_interval} seconds "
            f"(about {splay_interval // 60} minutes) before attempting to obtain the identity."
        )
        time.sleep(splay_interval)

    # Step 3: Obtain the identity certificate
    log.debug("Obtaining system identity")

    service = RegisterService(cp=uep)
    while cache.CloudTokenCache.is_valid():
        # While the server prepares the identity, it keeps sending status code 429
        # and a Retry-After header.
        try:
            service.register(org=None, jwt_token=token["token"])
            cache.CloudTokenCache.delete_cache()
            # The anonymous organization will have different entitlement certificates,
            # we need to refresh them.
            log.debug(
                "Replacing anonymous entitlement certificates "
                "with entitlement certificates linked to an anonymous organization."
            )
            report = entcertlib.EntCertUpdateAction().perform()
            log.debug(report)
            return
        except connection.RateLimitExceededException as exc:
            if exc.headers.get("Retry-After", None) is None:
                raise
            delay = int(exc.headers["Retry-After"])
            log.debug(
                f"Got response with status code {exc.code} and Retry-After header, "
                f"will try again in {delay} seconds."
            )
            time.sleep(delay)
        except Exception:
            raise

    # In theory, this should not happen, it means that something has gone wrong server-side.
    raise TimeoutError("The Candlepin JWT expired before we were able to register the system.")


def _main(args: "argparse.Namespace"):
    if not _is_enabled() and not args.force:
        log.info("The rhsmcertd process has been disabled by configuration.")
        sys.exit(ExitStatus.RHSMCERTD_DISABLED)

    log.debug("Running rhsmcertd worker.")

    # exit on SIGTERM, otherwise finally statements don't run
    # (one explanation: http://stackoverflow.com/a/41840796)
    # SIGTERM happens for example when systemd wants the service to stop
    # without finally statements, we get confusing behavior (ex. see bz#1431659)
    signal.signal(signal.SIGTERM, exit_on_signal)

    cp_provider: CPProvider = _create_cp_provider()

    if args.auto_register is True:
        if _is_registered():
            print(_("This system is already registered, ignoring request to automatically register."))
            log.debug("This system is already registered, skipping automatic registration.")
        else:
            print(_("Registering the system"))
            status: ExitStatus = _auto_register(cp_provider)
            sys.exit(status.value)

    if not ConsumerIdentity.existsAndValid():
        log.error(
            "Either the consumer is not registered or the certificates"
            + " are corrupted. Certificate update using daemon failed."
        )
        sys.exit(ExitStatus.LOCAL_CORRUPTION)

    print(_("Updating entitlement certificates & repositories."))

    uep: UEPConnection = cp_provider.get_consumer_auth_cp()
    # preload supported resources; serves as a way of failing before locking the repos
    uep.supports_resource(None)

    try:
        if args.autoheal:
            action_client = HealingActionClient()
        else:
            action_client = ActionClient()

        action_client.update()

        for update_report in action_client.update_reports:
            # FIXME: make sure we don't get None reports
            if update_report:
                print(update_report)

    except connection.ExpiredIdentityCertException as e:
        log.critical("System's identity certificate has expired.")
        raise e
    except connection.GoneException as ge:
        uuid = ConsumerIdentity.read().getConsumerId()
        # The GoneException carries information about a consumer deleted on the server.
        #
        # If this exception is raised and the `deleted_id` matches the current UUID,
        # we clean up the system. In theory, we could use a valid consumer certificate
        # to make a request for a different consumer UUID.
        if ge.deleted_id == uuid:
            log.info(
                f"Consumer profile '{uuid}' has been deleted from the server. "
                "Its local certificates will be archived to '/etc/pki/consumer.old/'."
            )
            managerlib.clean_all_data()

        raise ge


def main():
    logutil.init_logger()

    parser = ArgumentParser(usage=USAGE)
    parser.add_argument(
        "--autoheal",
        dest="autoheal",
        action="store_true",
        default=False,
        help="perform an autoheal check",
    )
    parser.add_argument("--force", dest="force", action="store_true", default=False, help=SUPPRESS)
    parser.add_argument(
        "--auto-register",
        dest="auto_register",
        action="store_true",
        default=False,
        help="perform auto-registration",
    )

    options: argparse.Namespace
    args: List[str]
    (options, args) = parser.parse_known_args()
    try:
        _main(options)
    except SystemExit as se:
        # sys.exit triggers an exception in older Python versions, which
        # in this case  we can safely ignore as we do not want to log the
        # stack trace. We need to check the code, since we want to signal
        # exit with failure to the caller. Otherwise, we will exit with 0
        if se.code:
            sys.exit(ExitStatus.UNKNOWN_ERROR)
    except Exception:
        log.exception("Error while updating certificates using daemon")
        print(_("Unable to update entitlement certificates and repositories"))
        sys.exit(ExitStatus.UNKNOWN_ERROR)


if __name__ == "__main__":
    main()
