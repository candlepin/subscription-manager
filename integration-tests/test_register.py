import os
import pytest
import contextlib
from pytest_client_tools.util import Version
from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str

import sh
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

"""
It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""


def test_register(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        private_proxy.Register("",
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {},
                               {},
                               locale)
    assert subman.is_registered
    

def test_register_with_org(external_candlepin, subman, test_config): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        private_proxy.Register(test_config.get("candlepin","org"),
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {},
                               {},
                               locale)
    assert subman.is_registered


@pytest.mark.parametrize("enable_content",["true","false"])
def test_register_with_enable_content(external_candlepin, subman, test_config, enable_content): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        private_proxy.Register(test_config.get("candlepin","org"),
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {
                                   "enable_content": get_variant(Str,enable_content)
                               },
                               {},
                               locale)
    assert subman.is_registered
   

def test_register_with_wrong_values(external_candlepin, subman, test_config, subtests): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")

        with subtests.test(msg="Register with wrong username"):
            with pytest.raises(DBusError) as excinfo:
                private_proxy.Register("",
                                       "wrong-username",
                                       test_config.get("candlepin","password"),
                                       {},
                                       {},
                                       locale)
            logger.debug(f"raised exception: {excinfo}")
            assert "Invalid username or password." in str(excinfo.value)
            assert not subman.is_registered
            
        with subtests.test(msg="Register with wrong password"):
            with pytest.raises(DBusError) as excinfo:
                private_proxy.Register("",
                                       test_config.get("candlepin","username"),
                                       "wrong-password",
                                       {},
                                       {},
                                       locale)
            logger.debug(f"raised exception: {excinfo}")
            assert "Invalid username or password." in str(excinfo.value)
            assert not subman.is_registered
            
        with subtests.test(msg="Register with wrong organization"):
            wrong_org="wrong-organization"
            with pytest.raises(DBusError) as excinfo:
                private_proxy.Register(wrong_org,
                                       test_config.get("candlepin","username"),
                                       test_config.get("candlepin","password"),
                                       {},
                                       {},
                                       locale)
            logger.debug(f"raised exception: {excinfo}")
            assert f"Organization {wrong_org} does not exist." in str(excinfo.value)
            assert not subman.is_registered


def test_get_environments(external_candlepin, subman, test_config):
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        response = private_proxy.GetEnvironments(test_config.get("candlepin","org") or "",
                                                 test_config.get("candlepin","username"),
                                                 test_config.get("candlepin","password"),
                                                 {},
                                                 {},
                                      locale)
