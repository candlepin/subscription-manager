import os
import pytest
import contextlib
from pytest_client_tools.util import Version
import conftest
from constants import RHSM, RHSM_CONFIG, RHSM_CONFIG_FILE_PATH
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str, get_native

import sh
import subprocess
import json
import logging
from  iniparse import SafeConfigParser
from funcy import first, group_by, second

logger = logging.getLogger(__name__)
    
def config_iter():
    parser = SafeConfigParser()
    parser.read(RHSM_CONFIG_FILE_PATH)
    for section in parser.sections():
        for option_name in parser.options(section):
            option_tuple = (f"{section}.{option_name}",parser.get(section,option_name))
            yield option_tuple

def config_sections():
    parser = SafeConfigParser()
    parser.read(RHSM_CONFIG_FILE_PATH)
    for section in parser.sections():
        yield section

def config_values_by_section():
    return group_by(lambda ii: first(first(ii).split(".")), config_iter())

@pytest.mark.parametrize("item_name,item_value", config_iter())
def test_get(item_name, item_value):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    """
    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    locale = os.environ.get("LANG", "")
    response = proxy.Get(item_name,locale)
    logger.debug(f"response from dbus call Get: {response}")
    assert item_value == get_native(response)

@pytest.mark.parametrize("section", config_sections())
def test_get_section(section):
    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    locale = os.environ.get("LANG", "")
    response = proxy.Get(section,locale)
    logger.debug(f"response from dbus call Get: {response}")
    section_values = get_native(response)
    logger.debug(section_values)
    
    origin_values_by_section = config_values_by_section()
    origin_section_values = origin_values_by_section[section]
    origin_section_keys = [second(first(ii).split(".")) for ii in origin_section_values]
    assert frozenset(origin_section_keys).issubset(frozenset(section_values.keys())),\
        "All fields from original must exists in the response. \
        There can be fields with default value in response that do not exist in the origin section"
    
    "all values should be the same"
    for full_key,origin_value in origin_section_values:
        key = second(full_key.split("."))
        assert origin_value == section_values[key]
    
def test_get_all():
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    """
    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    locale = os.environ.get("LANG", "")
    response = proxy.GetAll(locale)
    values_by_section = config_values_by_section()
    
    logger.debug(f"response from dbus call Get: {response}")
    logger.debug(f"fields read from {RHSM_CONFIG_FILE_PATH}: {values_by_section}")
    
    assert frozenset(values_by_section.keys()) == frozenset(response.keys()),\
        "GetAll method must return all sections in config file, nothing less, nothing more"
    
    for section_name in response.keys():
        section = get_native(response[section_name])
        origin_section = values_by_section[section_name]
        origin_section_keys = [second(first(ii).split(".")) for ii in origin_section]
        assert frozenset(origin_section_keys).issubset(frozenset(section.keys())),\
            "All fields from original must exists in the response. \
            There can be fields with default value in response that do not exist in the origin section"
        
        "all values should be the same"
        for full_key,origin_value in origin_section:
            key = second(full_key.split("."))
            assert origin_value == section[key]

def test_set():
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    """
    key="logging.default_log_level"
    values = frozenset(["DEBUG","INFO","TRACE"])

    proxy = RHSM.get_proxy(RHSM_CONFIG, interface_name=RHSM_CONFIG)
    locale = os.environ.get("LANG", "")

    origin_value = proxy.Get(key,locale)
    new_value = first(values - frozenset([get_native(origin_value)]))

    # set new value
    proxy.Set(key,get_variant("s",new_value),locale)

    # verify that Get returns new value
    new_returned_value = proxy.Get(key,locale)
    assert new_value == get_native(new_returned_value)

    # read config
    parser = SafeConfigParser()
    parser.read(RHSM_CONFIG_FILE_PATH)
    
    stored_value = parser.get(first(key.split(".")), second(key.split(".")))
    assert stored_value == get_native(new_returned_value),\
        f"Value must be stored in a config file {RHSM_CONFIG_FILE_PATH}"
