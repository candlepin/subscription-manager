#!/usr/bin/python

from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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
import logging

from subscription_manager import base_action_client

from subscription_manager.entcertlib import EntCertActionInvoker
from subscription_manager.identitycertlib import IdentityCertActionInvoker
from subscription_manager.healinglib import HealingActionInvoker
from subscription_manager.factlib import FactsActionInvoker
from subscription_manager.packageprofilelib import PackageProfileActionInvoker
from subscription_manager.installedproductslib import InstalledProductsActionInvoker
from subscription_manager.content_action_client import ContentActionClient
from subscription_manager.syspurposelib import SyspurposeSyncActionInvoker

log = logging.getLogger(__name__)


class ActionClient(base_action_client.BaseActionClient):

    def _get_libset(self):

        # TODO: replace with FSM thats progress through this async and wait/joins if needed
        self.entcertlib = EntCertActionInvoker()
        self.content_client = ContentActionClient()
        self.factlib = FactsActionInvoker()
        self.profilelib = PackageProfileActionInvoker()
        self.installedprodlib = InstalledProductsActionInvoker()
        self.idcertlib = IdentityCertActionInvoker()
        self.syspurposelib = SyspurposeSyncActionInvoker()

        # WARNING: order is important here, we need to update a number
        # of things before attempting to autoheal, and we need to autoheal
        # before attempting to fetch our certificates:
        lib_set = [self.entcertlib, self.idcertlib, self.content_client,
                   self.factlib, self.profilelib,
                   self.installedprodlib, self.syspurposelib]

        return lib_set


class HealingActionClient(base_action_client.BaseActionClient):
    def _get_libset(self):

        self.entcertlib = EntCertActionInvoker()
        self.installedprodlib = InstalledProductsActionInvoker()
        self.syspurposelib = SyspurposeSyncActionInvoker()
        self.healinglib = HealingActionInvoker()

        lib_set = [self.installedprodlib, self.syspurposelib, self.healinglib, self.entcertlib]

        return lib_set


# it may make more sense to have *Lib.cleanup actions?
# *Lib things are weird, since some are idempotent, but
# some arent. entcertlib/repolib .update can both install
# certs, and/or delete all of them.
class UnregisterActionClient(base_action_client.BaseActionClient):
    """CertManager for cleaning up on unregister.

    This class should not need a consumer id, or a uep connection, since it
    is running post unregister.
    """
    def _get_libset(self):

        self.entcertlib = EntCertActionInvoker()
        self.content_action_client = ContentActionClient()

        lib_set = [self.entcertlib, self.content_action_client]
        return lib_set


class ProfileActionClient(base_action_client.BaseActionClient):
    """
    This class should not need a consumer id, or a uep connection, since it
    is running post unregister.
    """
    def _get_libset(self):

        self.profilelib = PackageProfileActionInvoker()

        lib_set = [self.profilelib]
        return lib_set
