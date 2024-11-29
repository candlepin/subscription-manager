import os
import pytest
import contextlib
from pytest_client_tools.util import Version
import conftest
from constants import RHSM, RHSM_CONSUMER
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str

import sh
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

@pytest.mark.parametrize("status_of_registration",["registered","not_registered"])
def test_get_uuid(external_candlepin, subman, test_config, status_of_registration):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    """
    if status_of_registration == "registered":
        subman.register(username=test_config.get("candlepin","username"),
                        password=test_config.get("candlepin","password"),
                        org=test_config.get("candlepin","org") or "")
        conftest.loop_until(lambda: subman.is_registered)
        
    if status_of_registration == "not_registered":
        assert not subman.is_registered
        
    proxy = RHSM.get_proxy(RHSM_CONSUMER, interface_name=RHSM_CONSUMER)
    locale = os.environ.get("LANG", "")
    response = proxy.GetUuid(locale)
    logger.debug(f"response from dbus call GetUuid: {response}")

    if status_of_registration == "registered":
        assert subman.is_registered
        uuid_of_the_system = subman.uuid
        assert response == str(uuid_of_the_system)
        
    if status_of_registration == "not_registered":
        assert not subman.is_registered
        assert response == ""

