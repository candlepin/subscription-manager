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
This module is an interface to intentctl's IntentStore class from subscription-manager.
It contains methods for accessing/manipulating the local intent.json metadata file through IntentStore.
"""

import logging
log = logging.getLogger(__name__)

try:
    from intentctl.intentfiles import IntentStore, USER_INTENT
except ImportError:
    log.error("Could not import from module intentctl.")


def save_sla_to_intent_metadata(service_level):
    """
    Saves the provided service-level value to the local Intent Metadata (intent.json) file.
    If the service level provided is null or empty, the sla value to the local intent file is set to null.

    :param service_level: The service-level value to be saved in the intent file.
    :type service_level: str
    """

    if 'IntentStore' in globals():
        store = IntentStore.read(USER_INTENT)

        # if empty, set it to null
        if service_level is None or service_level == "":
            service_level = None

        store.set("service_level_agreement", service_level)
        store.write()
        log.info("Intent SLA value successfully saved locally.")
    else:
        log.error("IntentStore could not be imported. Intent SLA value not saved locally.")
