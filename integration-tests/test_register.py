import os
import pytest
import contextlib
from pytest_client_tools.util import Version
from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER

import sh
import subprocess
import json
import logging

log = logging.getLogger(__name__)

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
        private_proxy.Register("",#test_config.get("organization"),
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {},
                               {},
                               locale)
    assert subman.is_registered
    
