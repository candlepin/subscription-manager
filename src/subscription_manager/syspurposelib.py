# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2018 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
This module is an interface to syspurpose's SyspurposeStore class from subscription-manager.
It contains methods for accessing/manipulating the local syspurpose.json metadata file through SyspurposeStore.
"""

import logging
import json
import os
log = logging.getLogger(__name__)

try:
    from syspurpose.files import SyspurposeStore, USER_SYSPURPOSE
except ImportError:
    log.error("Could not import from module syspurpose.")
    SyspurposeStore = None
    USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

store = None
syspurpose = None


def save_sla_to_syspurpose_metadata(service_level):
    """
    Saves the provided service-level value to the local Syspurpose Metadata (syspurpose.json) file.
    If the service level provided is null or empty, the sla value to the local syspurpose file is set to null.

    :param service_level: The service-level value to be saved in the syspurpose file.
    :type service_level: str
    """

    if 'SyspurposeStore' in globals() and SyspurposeStore is not None:
        store = SyspurposeStore.read(USER_SYSPURPOSE)

        # if empty, set it to null
        if service_level is None or service_level == "":
            service_level = None

        store.set("service_level_agreement", service_level)
        store.write()
        log.info("Syspurpose SLA value successfully saved locally.")
    else:
        log.error("SyspurposeStore could not be imported. Syspurpose SLA value not saved locally.")


def save_role_to_syspurpose_metadata(role):
    """
    Save provided role value to the local Syspurpose Metadata (syspurpose.json) file.
    :param role: The value of role to be saved in the syspurpose file.
    :type role: str
    :return: None
    """

    if SyspurposeStore:
        store = SyspurposeStore.read(USER_SYSPURPOSE)

        if role is None or role == "":
            store.unset("role")
        else:
            store.set("role", role)
        store.write()
        return True
    else:
        log.error("SyspurposeStore could not be imported. Syspurpose role value not saved locally.")
        return False


def save_usage_to_syspurpose_metadata(usage):
    """
    Saves the provided usage value to the local Syspurpose Metadata (syspurpose.json) file.
    If the usage setting provided is null or empty, the usage value to the local syspurpose file is set to null.

    :param usage: The usage value to be saved in the syspurpose file.
    :type usage: str
    """

    if 'SyspurposeStore' in globals() and SyspurposeStore is not None:
        store = SyspurposeStore.read(USER_SYSPURPOSE)

        # if empty, set it to null
        if usage is None or usage == "":
            usage = None

        store.set("usage", usage)
        store.write()
        log.info("Syspurpose Usage value successfully saved locally.")
    else:
        log.error("SyspurposeStore could not be imported. Syspurpose Usage value not saved locally.")


def get_sys_purpose_store():
    """
    :return: Returns a singleton instance of the syspurpose store if it was imported.
             Otherwise None.
    """
    global store
    if store is not None:
        return store
    elif SyspurposeStore is not None:
        store = SyspurposeStore.read(USER_SYSPURPOSE)
    return store


def add(key, value):
    """
    An abstraction which uses the syspurpose store to add an item to a list.
    In the future this might have a backup functionality to be used when the syspurpose source
    is not on the system.
    :param key: The key of syspurpose to add the value to
    :param value: The value to be added to the list
    :return: The return value of the operation performed using syspurpose
    """
    store = get_sys_purpose_store()
    if store is not None:
        return store.add(key, value)


def add_all(key, values):
    """
    Extend a named list (key) with values. Just for convenience.
    :param key: The key of the syspurpose value to add to
    :param values: A list of values to add to key.
    :return:
    """
    return any(add(key, val) for val in values)


def remove(key, value):
    """
    Remove a value from the list specified by key.
    Uses the syspurpose code if available, if not presently does nothing.
    A backup functionality could be added in the future if in case syspurpose is not available.
    :param key: The name of the list to remove from.
    :param value: The value to remove.
    :return:
    """
    store = get_sys_purpose_store()
    if store is not None:
        return store.remove(key, value)


def remove_all(key, values):
    """
    Remove from a named list (key) the values in (values). Just for convenience.
    :param key: The key of the syspurpose value to remove from
    :param values: A list of values to remove from that key
    :return:
    """
    return any(remove(key, val) for val in values)


def set(key, value):
    """
    Set a (key) to the (value) using syspurpose store if available. If not available, do nothing.
    :param key: The name of the value to set.
    :param value: The value that should be set for (key).
    :return:
    """
    store = get_sys_purpose_store()
    if store is not None:
        return store.set(key, value)


def unset(key):
    """
    Unset a particular named value (key).
    :param key: The name of the value to unset.
    :return:
    """
    store = get_sys_purpose_store()
    if store is not None:
        return store.unset(key)


def write():
    """
    Write the values out using the syspurpose store if available. If not do nothing.
    :return:
    """
    store = get_sys_purpose_store()
    if store is not None:
        return store.write()


def read_syspurpose():
    """
    Reads the system purpose from the correct location on the file system.
    Makes an attempt to use a SyspurposeStore if available falls back to reading the json directly.
    :return: A dictionary containing the total syspurpose.
    """
    if SyspurposeStore is not None:
        try:
            syspurpose = SyspurposeStore.read(USER_SYSPURPOSE).contents
        except (OSError, IOError):
            syspurpose = {}
    else:
        try:
            syspurpose = json.load(open(USER_SYSPURPOSE))
        except (os.error, ValueError):
            # In the event this file could not be read treat it as empty
            syspurpose = {}
    return syspurpose
