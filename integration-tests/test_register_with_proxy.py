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

# TODO: is is necessary to enable log level DEBUG in /etc/rhsm/rhsm.conf.
#       log messages in /var/log/rhsm/rhsm.log file are a part of verification
#       process to prove a proxy was connected

def test_register_with_noauth_proxy(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6

    a message aka:
    2024-11-27 03:16:10,163 [DEBUG] subscription-manager:23907:MainThread @connection.py:773 - Using proxy: auto-services.usersys.redhat.com:3129
    should appear in /var/log/rhsm/rhsm.log file.
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
                               {
                                   "proxy_hostname": get_variant(Str,test_config.get("noauth_proxy","host")),
                                   "proxy_port": get_variant(Str,str(test_config.get("noauth_proxy","port")))
                                },
                               locale)
    
    assert subman.is_registered
    with open("/var/log/rhsm/rhsm.log","rt") as logfile:
        assert f"Using proxy:" in logfile.read()



        
def test_register_with_auth_proxy(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6

    a message aka:
    2024-11-27 03:16:10,163 [DEBUG] subscription-manager:23907:MainThread @connection.py:773 - Using proxy: auto-services.usersys.redhat.com:3129
    should appear in /var/log/rhsm/rhsm.log file.
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
                               {
                                   "proxy_hostname": get_variant(Str,test_config.get("auth_proxy","host")),
                                   "proxy_port": get_variant(Str,str(test_config.get("auth_proxy","port"))),
                                   "proxy_userame": get_variant(Str,str(test_config.get("auth_proxy","username"))),
                                   "proxy_password": get_variant(Str,str(test_config.get("auth_proxy","password")))
                                },
                               locale)
    
    assert subman.is_registered
    with open("/var/log/rhsm/rhsm.log","rt") as logfile:
        assert f"Using proxy:" in logfile.read()
        

