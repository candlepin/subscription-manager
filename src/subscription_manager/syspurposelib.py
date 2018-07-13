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
log = logging.getLogger(__name__)

try:
    from syspurpose.files import SyspurposeStore, USER_SYSPURPOSE
except ImportError:
    log.error("Could not import from module syspurpose.")


def save_sla_to_syspurpose_metadata(service_level):
    """
    Saves the provided service-level value to the local Syspurpose Metadata (syspurpose.json) file.
    If the service level provided is null or empty, the sla value to the local syspurpose file is set to null.

    :param service_level: The service-level value to be saved in the syspurpose file.
    :type service_level: str
    """

    if 'SyspurposeStore' in globals():
        store = SyspurposeStore.read(USER_SYSPURPOSE)

        # if empty, set it to null
        if service_level is None or service_level == "":
            service_level = None

        store.set("service_level_agreement", service_level)
        store.write()
        log.info("Syspurpose SLA value successfully saved locally.")
    else:
        log.error("SyspurposeStore could not be imported. Syspurpose SLA value not saved locally.")
