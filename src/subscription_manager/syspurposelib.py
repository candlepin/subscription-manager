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

from rhsm.connection import ConnectionException
from subscription_manager.cache import SyspurposeCache
from subscription_manager import certlib
from subscription_manager import injection as inj
from subscription_manager.utils import three_way_merge

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

# All names that represent syspurpose values locally
ROLE = 'role'
ADDONS = 'addons'
SERVICE_LEVEL = 'service_level_agreement'
USAGE = 'usage'

# Remote values keyed on the local ones
LOCAL_TO_REMOTE = {
    ROLE: 'role',
    ADDONS: 'addOns',
    SERVICE_LEVEL: 'serviceLevel',
    USAGE: 'usage'
}

# All known syspurpose attributes
ATTRIBUTES = [ROLE, ADDONS, SERVICE_LEVEL, USAGE]


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

    if 'SyspurposeStore' in globals() and SyspurposeStore is not None:
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


def read_syspurpose(raise_on_error=False):
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
            if raise_on_error:
                raise
            syspurpose = {}
    return syspurpose


def write_syspurpose(values):
    """
    Write the syspurpose to the file system.
    :param values:
    :return:
    """
    if SyspurposeStore is not None:
        sp = SyspurposeStore(USER_SYSPURPOSE)
        sp.contents = values
        sp.write()
    else:
        # Simple backup in case the syspurpose tooling is not installed.
        try:
            json.dump(values, open(USER_SYSPURPOSE), ensure_ascii=True, indent=2)
        except OSError:
            log.warning('Could not write syspurpose to %s' % USER_SYSPURPOSE)
            return False
    return True


class SyspurposeSyncActionInvoker(certlib.BaseActionInvoker):
    """
    Used by rhsmcertd to sync the syspurpose values locally with those from the Server.
    """

    def _do_update(self):
        action = SyspurposeSyncActionCommand()
        return action.perform()


class SyspurposeSyncActionReport(certlib.ActionReport):
    name = "Syspurpose Sync"

    def record_change(self, change):
        """
        Records the change detected by the three_way_merge function into a record in the report.
        :param change: A util.DiffChange object containing the recorded changes.
        :return: None
        """
        if change.source == 'remote':
            source = 'Entitlement Server'
        elif change.source == 'local':
            source = USER_SYSPURPOSE
        else:
            source = 'cached system purpose values'
        msg = None
        if change.in_base and not change.in_result:
            msg = "'{key}' removed by change from {source}".format(key=change.key,
                                                                     source=source)
        elif not change.in_base and change.in_result:
            msg = "'{key}' added with value '{value}' from change in {source}".format(
                    key=change.key, value=change.new_value, source=source
            )
        elif change.in_base and change.previous_value != change.new_value:
            msg = "'{key}' updated from '{old_value}' to '{new_value}' due to change in {source}"\
                .format(key=change.key, new_value=change.new_value,
                        old_value=change.previous_value, source=source)

        if msg:
            self._updates.append(msg)


class SyspurposeSyncActionCommand(object):
    """
    Sync the system purpose values, by performing a three-way merge between:
      - The last known shared state (SyspurposeCache)
      - The current values on the server
      - The current values on the file system
    """

    def __init__(self):
        self.report = SyspurposeSyncActionReport()
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = self.cp_provider.get_consumer_auth_cp()

    def perform(self, include_result=False):
        """
        Perform the action that this Command represents.
        :return:
        """
        result = {}
        try:
            result = self.sync()
        except ConnectionException as e:
            self.report._exceptions.append('Unable to sync syspurpose with server: %s' % str(e))
            self.report._status = 'Failed to sync system purpose'
        self.report._updates = "\n\t\t ".join(self.report._updates)
        log.debug("Syspurpose updated: %s" % self.report)
        if not include_result:
            return self.report
        else:
            return self.report, result

    def sync(self):
        """
        Actually do the sync between client and server.
        Saves the merged changes between client and server in the SyspurposeCache.
        :return: The synced values
        """
        if not self.uep.has_capability('syspurpose'):
            log.debug('Server does not support syspurpose, not syncing')
            return read_syspurpose()

        consumer_identity = inj.require(inj.IDENTITY)
        consumer = self.uep.getConsumer(consumer_identity.uuid)

        server_sp = {}
        sp_cache = SyspurposeCache()
        # Translate from the remote values to the local, filtering out items not known
        for attr in ATTRIBUTES:
            value = consumer.get(LOCAL_TO_REMOTE[attr])
            if value is None:
                value = ""
            server_sp[attr] = value

        try:
            filesystem_sp = read_syspurpose(raise_on_error=True)
        except (os.error, ValueError):
            self.report._exceptions.append(
                    'Cannot read local syspurpose, trying to update from server only'
            )
            result = server_sp
            log.debug('Unable to read local system purpose at  \'%s\'\nUsing the server values.'
                      % USER_SYSPURPOSE)
        else:
            cached_values = sp_cache.read_cache_only()
            result = three_way_merge(local=filesystem_sp, base=cached_values, remote=server_sp,
                                     on_change=self.report.record_change)

        sp_cache.syspurpose = result
        sp_cache.write_cache()

        write_syspurpose(result)
        addons = result.get(ADDONS)
        self.uep.updateConsumer(
                consumer_identity.uuid,
                role=result.get(ROLE) or "",
                addons=addons if addons is not None else "",
                service_level=result.get(SERVICE_LEVEL) or "",
                usage=result.get(USAGE) or ""
        )

        self.report._status = 'Successfully synced system purpose'

        log.debug('Updated syspurpose located at \'%s\'' % USER_SYSPURPOSE)

        return result
