# Copyright (c) 2017 Red Hat, Inc.
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

"""
This module provides service for system purpose
"""

import logging
from typing import Dict

from rhsm.connection import UEPConnection

from subscription_manager import injection as inj
from subscription_manager.i18n import ugettext as _
from subscription_manager.syspurposelib import (
    merge_syspurpose_values,
    write_syspurpose,
    get_sys_purpose_store,
)

from rhsmlib.file_monitor import SYSPURPOSE_WATCHER
from rhsmlib.dbus.server import Server

log = logging.getLogger(__name__)


class Syspurpose:
    def __init__(self, cp: UEPConnection) -> None:
        self.cp = cp
        self.identity = inj.require(inj.IDENTITY)
        self.purpose_status = {"status": "unknown"}
        self.owner = None
        self.valid_fields = None

    def get_syspurpose_status(self, on_date: str = None) -> Dict:
        """
        Get syspurpose status from candlepin server
        :param on_date: Date of the status
        :return: string code with status
        """
        if self.identity.is_valid() and self.cp.has_capability("syspurpose"):
            self.purpose_status = self.cp.getSyspurposeCompliance(self.identity.uuid, on_date)
        return self.purpose_status

    def get_owner_syspurpose_valid_fields(self) -> dict:
        """
        Get valid syspurpose fields from candlepin server for current owner
        :return: Dictionary with valid syspurpose fields
        """
        if self.identity.is_valid() and self.cp.has_capability("syspurpose"):
            self.owner = inj.require(inj.CURRENT_OWNER_CACHE)
            cache = inj.require(inj.SYSPURPOSE_VALID_FIELDS_CACHE)
            self.valid_fields = cache.read_data(uep=self.cp, identity=self.identity)
        return self.valid_fields

    def set_syspurpose_values(self, syspurpose_values: dict) -> dict:
        """
        Try to set system purpose values
        :param syspurpose_values: Dictionary with system purpose values
        :return: Dictionary with local result
        """
        Server.temporary_disable_dir_watchers({SYSPURPOSE_WATCHER})
        if self.identity.is_valid() and self.cp.has_capability("syspurpose"):
            local_result = merge_syspurpose_values(
                local=syspurpose_values, uep=self.cp, consumer_uuid=self.identity.uuid
            )
            write_syspurpose(local_result)
            synced_store = get_sys_purpose_store()
            sync_result = synced_store.sync()
            result = sync_result.result
        else:
            local_result = merge_syspurpose_values(local=syspurpose_values, remote={}, base={})
            write_syspurpose(local_result)
            result = local_result
        Server.enable_dir_watchers({SYSPURPOSE_WATCHER})

        return result

    @staticmethod
    def get_overall_status(status: str) -> str:
        """
        Return translated string representation syspurpose status
        :param status: syspurpose status
        :return: Translated string with status
        """
        # Status map has to be here, because we have to translate strings
        # when function is called (not during start of application) due to
        # rhsm.service which can run for very long time
        status_map = {
            "valid": _("Matched"),
            "invalid": _("Mismatched"),
            "partial": _("Partial"),
            "matched": _("Matched"),
            "mismatched": _("Mismatched"),
            "not specified": _("Not Specified"),
            "disabled": _("Disabled"),
            "unknown": _("Unknown"),
        }
        return status_map.get(status, status_map["unknown"])
