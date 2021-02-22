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
This module is an interface to syspurpose's SyncedStore class from subscription-manager.
It contains methods for accessing/manipulating the local syspurpose.json metadata file through SyncedStore.
"""

from rhsm.connection import ConnectionException
from subscription_manager import certlib
from subscription_manager import injection as inj
from syspurpose.files import SyncedStore, USER_SYSPURPOSE, CACHED_SYSPURPOSE

import logging
import json
import os

log = logging.getLogger(__name__)

store = None
syspurpose = None


def save_sla_to_syspurpose_metadata(uep, consumer_uuid, service_level):
    """
    Saves the provided service-level value to the local Syspurpose Metadata (syspurpose.json) file.
    If the service level provided is null or empty, the sla value to the local syspurpose file is set to null.
    when uep and consumer_uuid is not None, then service_level is also synced with candlepin server

    :param uep: The object with uep connection (connection to candlepin server)
    :param consumer_uuid: Consumer UUID
    :param service_level: The service-level value to be saved in the syspurpose file.
    :type service_level: str
    """

    if 'SyncedStore' in globals() and SyncedStore is not None:
        synced_store = SyncedStore(uep=uep, consumer_uuid=consumer_uuid)

        # if empty, set it to null
        if service_level is None or service_level == "":
            service_level = None

        synced_store.set("service_level_agreement", service_level)
        synced_store.finish()
        log.debug("Syspurpose SLA value successfully saved locally.")
    else:
        log.error("SyspurposeStore could not be imported. Syspurpose SLA value not saved locally.")


def get_sys_purpose_store():
    """
    :return: Returns a singleton instance of the syspurpose store if it was imported.
             Otherwise None.
    """
    global store
    if store is not None:
        return store
    elif SyncedStore is not None:
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        uuid = inj.require(inj.IDENTITY).uuid
        store = SyncedStore(uep, consumer_uuid=uuid)
    return store


def read_syspurpose(synced_store=None, raise_on_error=False):
    """
    Reads the system purpose from the correct location on the file system.
    Makes an attempt to use a SyspurposeStore if available falls back to reading the json directly.
    :return: A dictionary containing the total syspurpose.
    """
    if SyncedStore is not None:
        if synced_store is None:
            synced_store = SyncedStore(None)
        try:
            content = synced_store.get_local_contents()
        except (OSError, IOError):
            content = {}
    else:
        try:
            content = json.load(open(USER_SYSPURPOSE))
        except (os.error, ValueError, IOError):
            # In the event this file could not be read treat it as empty
            if raise_on_error:
                raise
            content = {}
    return content


def write_syspurpose(values):
    """
    Write the syspurpose to the file system.
    :param values:
    :return:
    """
    if SyncedStore is not None:
        sp = SyncedStore(None)
        sp.update_local(values)
    else:
        # Simple backup in case the syspurpose tooling is not installed.
        try:
            json.dump(values, open(USER_SYSPURPOSE), ensure_ascii=True, indent=2)
        except OSError:
            log.warning('Could not write syspurpose to %s' % USER_SYSPURPOSE)
            return False
    return True


def write_syspurpose_cache(values):
    """
    Write to the syspurpose cache on the file system.
    :param values:
    :return:
    """
    try:
        json.dump(values, open(CACHED_SYSPURPOSE, 'w'), ensure_ascii=True, indent=2)
    except OSError:
        log.warning('Could not write to syspurpose cache %s' % CACHED_SYSPURPOSE)
        return False
    return True


def get_syspurpose_valid_fields(uep=None, identity=None):
    """
    Try to get valid syspurpose fields provided by candlepin server
    :param uep: connection of candlepin server
    :param identity: current identity of registered system
    :return: dictionary with valid fields
    """
    valid_fields = {}
    cache = inj.require(inj.SYSPURPOSE_VALID_FIELDS_CACHE)
    syspurpose_valid_fields = cache.read_data(uep, identity)
    if 'systemPurposeAttributes' in syspurpose_valid_fields:
        valid_fields = syspurpose_valid_fields['systemPurposeAttributes']
    return valid_fields


def merge_syspurpose_values(local=None, remote=None, base=None, uep=None, consumer_uuid=None):
    """
    Try to do three-way merge of local, remote and base dictionaries.
    Note: when remote is None, then this method will call REST API.
    :param local: dictionary with local values
    :param remote: dictionary with remote values
    :param base: dictionary with cached values
    :param uep: object representing connection to canlepin server
    :param consumer_uuid: UUID of consumer
    :return: Dictionary with local result
    """

    if SyncedStore is None:
        return {}

    synced_store = SyncedStore(uep=uep, consumer_uuid=consumer_uuid)

    if local is None:
        local = synced_store.get_local_contents()
    if remote is None:
        remote = synced_store.get_remote_contents()
    if base is None:
        base = synced_store.get_cached_contents()

    result = synced_store.merge(
        local=local,
        remote=remote,
        base=base
    )
    local_result = {key: result[key] for key in result if result[key]}
    log.debug('local result: %s ' % local_result)
    return local_result


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

    """
    The base method formatting does not fit the massages we are seeing here
    BZ #1789457
    """
    def format_exceptions(self):
        buf = ''
        for e in self._exceptions:
            buf += str(e).strip()
            buf += '\n'
        return buf


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
        consumer_uuid = inj.require(inj.IDENTITY).uuid

        try:
            store = SyncedStore(
                uep=self.uep,
                consumer_uuid=consumer_uuid,
                on_changed=self.report.record_change
            )
            result = store.sync()
        except ConnectionException as e:
            self.report._exceptions.append('Unable to sync syspurpose with server: %s' % str(e))
            self.report._status = 'Failed to sync system purpose'
        self.report._updates = "\n\t\t ".join(self.report._updates)
        log.debug("Syspurpose updated: %s" % self.report)
        if not include_result:
            return self.report
        else:
            return self.report, result
