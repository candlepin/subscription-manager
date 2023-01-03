import logging
import socket
import time
import os
from typing import Callable, Dict, Any, Optional

from rhsm.connection import DeviceAuthConnection, UEPConnection

from rhsmlib.services import exceptions

from subscription_manager import injection as inj
from subscription_manager import managerlib
from subscription_manager import syspurposelib
from subscription_manager.i18n import ugettext as _
from subscription_manager.cp_provider import CPProvider
from subscription_manager.cli import system_exit

log = logging.getLogger(__name__)


class OAuthRegisterService:
    _default_polling_interval: int = 5

    def __init__(self, cp: UEPConnection) -> None:
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)
        self.facts = inj.require(inj.FACTS)
        self.identity = inj.require(inj.IDENTITY)
        self.cp: UEPConnection = cp
        self.device_auth_connection: DeviceAuthConnection = self._setup_device_auth_connection()

    def _setup_device_auth_connection(self) -> DeviceAuthConnection:
        candlepin_status = self.cp.getStatus()
        self._validate_device_auth_info(candlepin_status)

        auth_url = candlepin_status["deviceAuthUrl"]
        client_id = candlepin_status["deviceAuthClientId"]
        scope = candlepin_status["deviceAuthScope"]
        realm = candlepin_status["keycloakRealm"]
        return DeviceAuthConnection(auth_url, client_id, scope, realm)

    def initialize_device_auth(self) -> Optional[Dict[str, Any]]:
        print("Auth URL: {auth_host}, Handler: {handler}, Client Id: {client_id}, Scope: {scope}".format(
            auth_host=self.device_auth_connection.host,
            handler=self.device_auth_connection.handler,
            client_id=self.device_auth_connection.client_id,
            scope=self.device_auth_connection.scope
        ))
        return self.device_auth_connection.attempt_device_auth_request()

        """
        # Hard-code handler/url for now since candlepin server is returning incorrect values.
        # TODO: Replace hard-coded host url with: device_auth_info["auth_url"]
        handler = "/auth"
        self.cp_provider.set_connection_info(
            host=device_auth_info["auth_url"],
            ssl_port=443,
            handler=handler
        )
        uep = self.cp_provider.get_no_auth_cp()
        oauth_resp_content = uep.initializeDeviceAuth(
            client_id=device_auth_info["client_id"],
            scope=device_auth_info["scope"]
        )
        return oauth_resp_content
        """

    def poll_oauth_provider(self, oauth_login_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._validate_oauth_login_data(oauth_login_data)

        # Set the polling interval to the provided server value, or the default if unavailable.
        polling_interval = float(oauth_login_data.get("interval"))
        if polling_interval is None:
            polling_interval = self._default_polling_interval

        # Set the login expiration time
        login_expiration_time = int(oauth_login_data["expires_in"])

        # Setup connection
        polling_connection = DeviceAuthConnection(
            f"https://{self.device_auth_connection.host}/auth",
            self.device_auth_connection.client_id,
            self.device_auth_connection.scope,
            self.device_auth_connection.realm
        )

        elapsed_time: int = 0
        resp_received: bool = False
        access_token_resp: Optional[Dict[str, Any]] = None
        try:
            while not resp_received:
                if elapsed_time > login_expiration_time:
                    system_exit(os.EX_NOTFOUND, "OAuth device code not provided, cancelled authorization process.")

                # Query the OAuth provider to check if the user has provided a login code.
                print("Querying OAuth provider for device authorization response...")
                access_token_resp = polling_connection.poll_device_auth_token(
                    device_code=oauth_login_data["device_code"]
                )
                if access_token_resp is not None:
                    if access_token_resp["status"] == 400:
                        print("Authorization pending...")
                    elif access_token_resp["status"] == 404:
                        system_exit(os.EX_UNAVAILABLE, "Invalid authorization content received.")
                    else:
                        resp_received = True
                        break

                time.sleep(polling_interval)
                elapsed_time += polling_interval
            if access_token_resp is not None:
                access_token_resp = polling_connection.conn._extract_content_from_response(access_token_resp)
            return access_token_resp
        except KeyboardInterrupt:
            system_exit(os.EX_SOFTWARE, "OAuth device authorization process cancelled by user.")

    def _validate_device_auth_info(self, device_auth_info: Dict[str, Any]):
        if not isinstance(device_auth_info, dict):
            raise exceptions.ValidationError("Oauth device capability data could not be retrieved from the candlepin status.")
        if device_auth_info.get("deviceAuthUrl") is None:
            raise exceptions.ValidationError("A device authorization url could not be retrieved from the candlepin status.")
        if device_auth_info.get("deviceAuthClientId") is None:
            raise exceptions.ValidationError("A device authorization client Id could not be retrieved from the candlepin status.")
        if device_auth_info.get("deviceAuthScope") is None:
            raise exceptions.ValidationError("A device authorization scope could not be retrieved from the candlepin status.")
        if device_auth_info.get("deviceAuthRealm") is None:
            raise exceptions.ValidationError("A device authorization realm could not be retrieved from the candlepin status.")

    def _validate_oauth_login_data(self, oauth_login_data: Dict[str, Any]):
        if not isinstance(oauth_login_data, dict):
            raise exceptions.ValidationError("Oauth login dictionary data must be provided to authorize the device.")
        if oauth_login_data.get("device_code") is None:
            raise exceptions.ValidationError("A device_code must be provided to verify the device.")
        if oauth_login_data.get("user_code") is None:
            raise exceptions.ValidationError("A user_code must be provided to verify the device.")
        if oauth_login_data.get("verification_uri") is None:
            raise exceptions.ValidationError("A verificaiton_uri must be provided to verify the device on the authorization server.")
        if oauth_login_data.get("expires_in") is None:
            raise exceptions.ValidationError("The lifetime of the device and user code must be provided.")
