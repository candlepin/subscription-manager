import logging
import socket
import time
from typing import Callable, Dict, Any, Optional

from rhsm.connection import UEPConnection

from rhsmlib.services import exceptions

from subscription_manager import injection as inj
from subscription_manager import managerlib
from subscription_manager import syspurposelib
from subscription_manager.i18n import ugettext as _
from subscription_manager.cp_provider import CPProvider

log = logging.getLogger(__name__)


class OAuthRegisterService:
    _default_polling_interval: int = 5

    def __init__(self, cp: UEPConnection, cp_provider: CPProvider) -> None:
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)
        self.facts = inj.require(inj.FACTS)
        self.identity = inj.require(inj.IDENTITY)
        self.cp_provider: CPProvider = cp_provider
        self.cp: UEPConnection = cp

    def get_device_auth_capability(self) -> Optional[Dict[str, Any]]:
        candlepin_status = self.cp.getStatus()
        if candlepin_status is None:
            return None
        if "device_auth" not in candlepin_status.get("managerCapabilities", []):
            return None
        # Hard-code client_id since /status is responding with 'rhsm-api' instead of 'subscription-manager'
        return {
            "auth_url": candlepin_status.get("deviceAuthUrl"),
            "client_id": "subscription-manager",
            "scope": candlepin_status.get("deviceAuthScope")
        }

    def initialize_device_auth(self, device_auth_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._validate_oauth_capability_data(device_auth_info)
        if device_auth_info is None:
            return None
        if None in device_auth_info.values():
            raise exceptions.ValidationError("Server has not provided required device authorization data.")
        print("Auth URL: {auth_host}, Client Id: {client_id}, Scope: {scope}".format(
            auth_host=device_auth_info["auth_url"],
            client_id=device_auth_info["client_id"],
            scope=device_auth_info["scope"]
        ))

        # Hard-code handler/url for now since candlepin server is returning incorrect values.
        # TODO: Replace hard-coded host url with: device_auth_info["auth_url"]
        handler = "/auth"
        self.cp_provider.set_connection_info(
            host="sso.stage.redhat.com",
            ssl_port=443,
            handler=handler
        )
        uep = self.cp_provider.get_no_auth_cp()
        oauth_resp_content = uep.initializeDeviceAuth(
            client_id=device_auth_info["client_id"],
            scope=device_auth_info["scope"]
        )
        return oauth_resp_content

    def poll_oauth_provider(self, client_id: str, oauth_login_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._validate_oauth_login_data(oauth_login_data)
        if not isinstance(client_id, str):
            raise exceptions.ValidationError("A client_id must be provided to verify the device.")

        # Set the polling interval to the provided server value, or the default if unavailable.
        # FIXME: the polling interval should be in seconds, not miliseconds but the auth server
        # responds with intervals in the 100s (600 in stage) which can't be right...
        polling_interval = float(oauth_login_data.get("interval")) / 100
        if polling_interval is None:
            polling_interval = self._default_polling_interval

        # Set the login expiration time:
        login_expiration_time = int(oauth_login_data["expires_in"])

        # Setup connection
        handler = "/auth"
        self.cp_provider.set_connection_info(
            host="sso.stage.redhat.com",
            ssl_port=443,
            handler=handler
        )
        uep = self.cp_provider.get_no_auth_cp()

        elapsed_time: int = 0
        resp_received: bool = False
        access_token_resp = None
        try:
            while not resp_received:
                print(elapsed_time)
                if elapsed_time > 5:
                    print("OAuth device code not provided, cancelled authorization process.")
                    return None

                # Query the OAuth provider to check if the user has provided a login code.
                print("Querying OAuth provider for device authorization response...")
                access_token_resp = uep.pollDeviceAuthAccessToken(
                    client_id=client_id,
                    device_code=oauth_login_data["device_code"]
                )
                if access_token_resp is not None:
                    if access_token_resp['status'] == 400:
                        print("Authorization pending...")
                    else:
                        resp_received = True

                time.sleep(polling_interval)
                elapsed_time += polling_interval
            return access_token_resp
        except KeyboardInterrupt:
            print("OAuth device authorization process cancelled by user.")
            return None

    def _validate_oauth_capability_data(self, client_data: Dict[str, Any]):
        if not isinstance(client_data, dict):
            raise exceptions.ValidationError("Oauth device capability dictionary data must be provided to authorize the device.")
        if client_data.get("auth_url") is None:
            raise exceptions.ValidationError("An auth_url must be provided to verify the device.")
        if client_data.get("client_id") is None:
            raise exceptions.ValidationError("A client_id must be provided to verify the end-user.")
        if client_data.get("scope") is None:
            raise exceptions.ValidationError("A scope must be provided to verify the end-user.")

    def _validate_oauth_login_data(self, oauth_login_data: Dict[str, Any]):
        if not isinstance(oauth_login_data, dict):
            raise exceptions.ValidationError("Oauth login dictionary data must be provided to authorize the device.")
        if oauth_login_data.get("device_code") is None:
            raise exceptions.ValidationError("A device_code must be provided to verify the device.")
        if oauth_login_data.get("user_code") is None:
            raise exceptions.ValidationError("A user_code must be provided to verify the end-user.")
        if oauth_login_data.get("verification_uri") is None:
            raise exceptions.ValidationError("A verificaiton_uri must be provided to verify the end-user on the authorization server.")
        if oauth_login_data.get("expires_in") is None:
            raise exceptions.ValidationError("The lifetime of the device and user code must be provided.")
