import logging
import os

from dasbus.connection import MessageBus
from gi.repository import Gio

import gi

gi.require_version("Gio", "2.0")

logger = logging.getLogger(__name__)


class RHSMPrivateBus(MessageBus):
    """Representation of RHSM private bus connection that can be used as a context manager."""

    def __init__(self, rhsm_register_server_proxy, *args, **kwargs):
        """Representation of RHSM private bus connection that can be used as a context manager.

        :param rhsm_register_server_proxy: DBus proxy for the RHSM RegisterServer object
        """
        super().__init__(*args, **kwargs)
        self._rhsm_register_server_proxy = rhsm_register_server_proxy
        self._private_bus_address = None

    def __enter__(self):
        logger.debug("subscription: starting RHSM private DBus session")
        locale = os.environ.get("LANG", "")
        self._private_bus_address = self._rhsm_register_server_proxy.Start(locale)
        logger.debug("subscription: RHSM private DBus session has been started")
        return self

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        logger.debug("subscription: shutting down the RHSM private DBus session")
        self.disconnect()
        locale = os.environ.get("LANG", "")
        self._rhsm_register_server_proxy.Stop(locale)
        logger.debug("subscription: RHSM private DBus session has been shutdown")

    def _get_connection(self):
        """Get a connection to RHSM private DBus session."""
        # the RHSM private bus address is potentially sensitive
        # so we will not log it
        logger.info("Connecting to the RHSM private DBus session.")
        return self._provider.get_addressed_bus_connection(
            bus_address=self._private_bus_address, flags=Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
        )
