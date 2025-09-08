# Copyright (c) 2024 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

from constants import RHSM, RHSM_CONFIG
from funcy import first
from utils import read_ini_file, loop_until
import pytest
from dasbus.typing import get_native, get_variant, Str
import logging

logger = logging.getLogger(__name__)

SECS_TO_WAIT = 10  # ... for a dbus signal to appear in dbus monitor


"""
Integration test for DBus RHSM Config Object.

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#configuration
for more details.

Main use cases are presented in this file.
"""

# each call uses standard english locale
locale = "en_US.UTF-8"


def with_id(iterator):
    """
    The function returns list of pytest.params with id of a param.
    The appended id helps to see well described test names
    at pytest log output.

    iterator: Iterator[(key: String, value: String)]
        - description of the param (ie. id) is taken from 'key'
    returns: List[pytest.Param]
    """
    for item in iterator:
        yield pytest.param(item, id=item[0])


@pytest.mark.parametrize("item", with_id(read_ini_file("/etc/rhsm/rhsm.conf")))
def test_config_get(any_candlepin, item):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    and method Config.Get

    The method should provide value for each key in the config file /etc/rhsm/rhsm.conf
    """
    (key, value_in_the_config_file) = item
    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    value_in_response = proxy.Get(key, locale)
    assert value_in_response.get_string() == value_in_the_config_file


def test_config_get_all(any_candlepin):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    and method Config.GetAll

    The method should provide all values from the config file /etc/rhsm/rhsm.conf
    """
    proxy = RHSM.get_proxy(object_path=RHSM_CONFIG.object_path, interface_name=RHSM_CONFIG.interface_name)
    response = proxy.GetAll(locale)

    # an example of response:
    # {'server': GLib.Variant('a{ss}', {'hostname': 'subscription.rhsm.redhat.com', 'insecure': '0'}),
    #  'rhsm': GLib.Variant('a{ss}', {'progress_messages': '1', 'inotify': '1'}),
    #  'logging': GLib.Variant('a{ss}', {'default_log_level': 'INFO'})}

    def pairs(response):
        """
        The function transforms all dbus GLib.Variant structures into python dicts
        It returns a list of (key:String, value:String)
              ... the key is the whole path to a value.
        """
        for section, section_properties in response.items():
            for prop, value in get_native(section_properties).items():
                yield (f"{section}.{prop}", value)

    properties_in_file = dict(read_ini_file("/etc/rhsm/rhsm.conf"))
    properties_in_response = dict(pairs(response))
    # A method GetAll returns more properties than that are stored in the config file.
    # The method returns even default values.
    # That's why it is necessary to verify that only values in the file have the same value.
    for key, value in properties_in_file.items():
        assert value == properties_in_response[key]


DEFAULT_LOG_LEVEL_KEY = "logging.default_log_level"
LOG_LEVELS = ("INFO", "DEBUG", "ERROR", "WARNING")


@pytest.mark.parametrize("log_level", LOG_LEVELS)
def test_config_set(any_candlepin, log_level, dbus_current_signals):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    and method Config.Set

    The method should set property in the config file /etc/rhsm/rhsm.conf
    A DBus event ConfigChanges should be emitted too.

    The test verifies that:
    - a property is changed in the file
    - a dbus signal ConfigChanged is emitted
    """
    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    proxy.Set(DEFAULT_LOG_LEVEL_KEY, get_variant(Str, log_level), locale)

    properties_in_the_file = dict(read_ini_file("/etc/rhsm/rhsm.conf"))
    assert log_level == properties_in_the_file[DEFAULT_LOG_LEVEL_KEY]

    logger.info("an assertation for DBus signal to appear is temporary disabled - see CCT-1525 for details")

    # assert loop_until(
    #     lambda: len(dbus_current_signals.read()) > 0, poll_sec=1, timeout_sec=SECS_TO_WAIT
    # ), f"DBus signals should appear in {SECS_TO_WAIT} seconds"
    # assert "ConfigChanged" in [signal[1] for signal in dbus_current_signals.read()]


def test_config_set_all(any_candlepin, dbus_current_signals):
    """
    A DBus method SetAll sets many parameters in the file /etc/rhsm/rhsm.conf
    A test will use logging section to play with.

    [logging]
    default_log_level = WARNING

    This test verifies that
    - the properties are changed in the config file after SetAll method is used
    - a dbus signal ConfigChanged is emitted
    """

    KEYS_TO_SET = (
        "logging.default_log_level",
        "logging.subscription_manager",
        "logging.subscription_manager.managercli",
        "logging.rhsm",
        "logging.rhsm.connection",
        "logging.rhsm-app",
        "logging.rhsmcertd",
    )

    def unused_value(key):
        """a method finds a value not used for the given key in a config file"""
        properties_in_file = dict(read_ini_file("/etc/rhsm/rhsm.conf"))
        current_value = properties_in_file.get(key, "")
        return first(frozenset(LOG_LEVELS) - frozenset([current_value]))

    properties_with_new_value = dict((key, get_variant(Str, unused_value(key))) for key in KEYS_TO_SET)

    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    proxy.SetAll(properties_with_new_value, locale)

    properties_in_the_file = dict(
        pair for pair in read_ini_file("/etc/rhsm/rhsm.conf") if pair[0] in KEYS_TO_SET
    )

    # all stored properties should have new value
    for key, value in properties_in_the_file.items():
        assert value == get_native(properties_with_new_value[key])

    logger.info("an assertation for DBus signal to appear is temporary disabled - see CCT-1525 for details")

    # assert loop_until(
    #     lambda: len(dbus_current_signals.read()) > 0, poll_sec=1, timeout_sec=SECS_TO_WAIT
    # ), f"DBus signals should appear in {SECS_TO_WAIT} seconds"

    # assert "ConfigChanged" in [signal[1] for signal in dbus_current_signals.read()]


def test_config_signal_is_emitted(any_candlepin, subman, dbus_current_signals):
    """
    A DBus signal ConfigChanged should appear when a config file /etc/rhsm/rhsm.conf is changed.

    This test verifies that the signal is emitted even a third party software (or user) changes the file.

    A test will use logging section to play with.
    """
    subman.config(logging_default_log_level="DEBUG")
    assert loop_until(
        lambda: len(dbus_current_signals.read()) > 0, poll_sec=1, timeout_sec=SECS_TO_WAIT
    ), f"DBus signals should appear in {SECS_TO_WAIT} seconds"

    assert "ConfigChanged" in [signal[1] for signal in dbus_current_signals.read()]
