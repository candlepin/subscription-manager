import logging
import os
import pytest
from datetime import datetime
from dasbus.connection import MessageBus
from gi.repository import Gio
import multiprocessing
from dasbus.loop import EventLoop
from constants import RHSM, RHSM_CONFIG

import gi

gi.require_version("Gio", "2.0")

logger = logging.getLogger(__name__)


class RHSMPrivateBus(MessageBus):
    """
    Representation of RHSM private bus connection that can be used as a context manager.
    """

    def __init__(self, rhsm_register_server_proxy, *args, **kwargs):
        """
        Representation of RHSM private bus connection that can be used as a context manager.

        :param rhsm_register_server_proxy: DBus proxy for the RHSM RegisterServer object
        """
        super().__init__(*args, **kwargs)
        self._rhsm_register_server_proxy = rhsm_register_server_proxy
        self._private_bus_address = None

    def __enter__(self):
        locale = os.environ.get("LANG", "")
        self._private_bus_address = self._rhsm_register_server_proxy.Start(locale)
        return self

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        self.disconnect()
        locale = os.environ.get("LANG", "")
        self._rhsm_register_server_proxy.Stop(locale)

    def _get_connection(self):
        """
        Get a connection to RHSM private DBus session.
        """
        # the RHSM private bus address is potentially sensitive
        # so we will not log it
        return self._provider.get_addressed_bus_connection(
            bus_address=self._private_bus_address, flags=Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
        )


class DBusSignals:
    """
    A class used by a fixture dbus_current_signals.
    A class instance remembers a datetime of a test's start.
    I will provide signals (provided by 'dbus_signals' fixture) that are newer
    than a start of the test.
    """

    def __init__(self, since, signals):
        self.since = since
        self.signals = signals

    def read(self):
        """
        A method for a test to read all signals captured by dbus monitor.
        The method provides all signals that are emitted after the test begins.
        """
        return [signal for signal in self.signals if signal[0] >= self.since]


@pytest.fixture
def dbus_current_signals(dbus_signals):
    """
    A fixture used by tests.
    It is a gate to dbus monitor for a test to get current dbus signals.
    """
    return DBusSignals(datetime.now(), dbus_signals)


@pytest.fixture(scope="session", autouse=True)
def dbus_signals():
    """
    A fixture that provides a shared object (dbus signals) across processes.
    It is used internally to create an object for dbus signals.
    """
    ctx = multiprocessing.get_context("spawn")
    manager = ctx.Manager()
    yield manager.list()


def listen_on_event(events):
    """
    A process middleware to run a dasbus loop. The loop requires its own process.
    There are subscriptions to DBus events in a callback function.
    The function listens on Config/ConfigChanged events
    - it saves the events into a shared object provided by 'dbus_signals'
    """
    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)

    def callback():
        events.append((datetime.now(), "ConfigChanged"))

    proxy.ConfigChanged.connect(callback)
    loop = EventLoop()
    loop.run()


@pytest.fixture(scope="session", autouse=True)
def dbus_listener(dbus_signals):
    """
    An automatic fixture that fires up the whole dbus monitor process
    """
    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(target=listen_on_event, args=(dbus_signals,))
    process.start()

    yield

    if process is not None:
        process.terminate()
