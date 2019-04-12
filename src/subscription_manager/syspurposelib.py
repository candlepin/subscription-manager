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

import logging
import json
import os
log = logging.getLogger(__name__)

try:
    from syspurpose.sync import sync
except ImportError:
    def sync(uep, consumer_uuid, command=None, report=None):
        log.debug("Syspurpose module unavailable, not syncing")
        return read_syspurpose()

try:
    from syspurpose.files import SyncedStore, USER_SYSPURPOSE
except ImportError:
    log.debug("Could not import from module syspurpose.")
    SyncedStore = None
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

    if 'SyncedStore' in globals() and SyncedStore is not None:
        store = SyncedStore(None)

        # if empty, set it to null
        if service_level is None or service_level == "":
            service_level = None

        store.set("service_level_agreement", service_level)
        store.finish()
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


def read_syspurpose(raise_on_error=False):
    """
    Reads the system purpose from the correct location on the file system.
    Makes an attempt to use a SyspurposeStore if available falls back to reading the json directly.
    :return: A dictionary containing the total syspurpose.
    """
    if SyncedStore is not None:
        try:
            syspurpose = SyncedStore(None).get_local_contents()
        except (OSError, IOError):
            syspurpose = {}
    else:
        try:
            syspurpose = json.load(open(USER_SYSPURPOSE))
        except (os.error, ValueError, IOError):
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
        consumer_uuid = inj.require(inj.IDENTITY).uuid

        try:
            store = SyncedStore(uep=self.uep,
                                        consumer_uuid=consumer_uuid,
                                        report=self.report,
                                        on_changed=self.report.record_change)
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
