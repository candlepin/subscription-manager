#!/usr/bin/python
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

import gettext
import logging

from rhsm.connection import GoneException, ExpiredIdentityCertException

from subscription_manager.entcertlib import EntCertActionInvoker
from subscription_manager.identitycertlib import IdentityCertActionInvoker
from subscription_manager.healinglib import HealingActionInvoker
from subscription_manager.factlib import FactsActionInvoker
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.packageprofilelib import PackageProfileActionInvoker
from subscription_manager.installedproductslib import InstalledProductsActionInvoker
from subscription_manager import injection as inj

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


class BaseActionClient(object):
    """
    An object used to update the certficates, yum repos, and facts for the system.
    """

    # can we inject both of these?
    def __init__(self, facts=None):

        self.facts = facts

        self._libset = self._get_libset()
        self.lock = inj.require(inj.ACTION_LOCK)
        self.report = None
        self.update_reports = []

    def _get_libset(self):
        return []

    def update(self, autoheal=False):
        """
        Update I{entitlement} certificates and corresponding
        yum repositiories.
        @return: A list of update reports
        @rtype: list
        """
        lock = self.lock

        # TODO: move to using a lock context manager
        try:
            lock.acquire()
            self.update_reports = self._run_updates(autoheal)
        finally:
            lock.release()

    def _run_update(self, lib):
        update_report = None

        try:
            update_report = lib.update()
        # see bz#852706, reraise GoneException so that
        # consumer cert deletion works
        except GoneException, e:
            raise
        # raise this so it can be exposed clearly
        except ExpiredIdentityCertException, e:
            raise
        except Exception, e:
            log.warning("Exception caught while running %s update" % lib)
            log.exception(e)

        if update_report:
            update_report.print_exceptions()

        return update_report

    def _run_updates(self, autoheal):

        update_reports = []

        for lib in self._libset:
            update_report = self._run_update(lib)

            # a map/dict may make more sense here
            update_reports.append(update_report)

        return update_reports


class ActionClient(BaseActionClient):

    def _get_libset(self):
        identity = inj.require(inj.IDENTITY)
        if identity.is_valid():
            self.entcertlib = EntCertActionInvoker()
            self.factlib = FactsActionInvoker()
            self.profilelib = PackageProfileActionInvoker()
            self.installedprodlib = InstalledProductsActionInvoker()
            self.idcertlib = IdentityCertActionInvoker()

            # WARNING: order is important here, we need to update a number
            # of things before attempting to autoheal, and we need to autoheal
            # before attempting to fetch our certificates:
            return [self.entcertlib, self.idcertlib,
                       self.factlib, self.profilelib,
                       self.installedprodlib]

        # In the disconnected case, we only need to run repolib
        self.repolib = RepoActionInvoker()
        return [self.repolib]


class HealingActionClient(BaseActionClient):
    def _get_libset(self):

        self.entcertlib = EntCertActionInvoker()
        self.installedprodlib = InstalledProductsActionInvoker()
        self.healinglib = HealingActionInvoker()

        lib_set = [self.installedprodlib, self.healinglib, self.entcertlib]

        return lib_set


# it may make more sense to have *Lib.cleanup actions?
# *Lib things are weird, since some are idempotent, but
# some arent. entcertlib/repolib .update can both install
# certs, and/or delete all of them.
class UnregisterActionClient(BaseActionClient):
    """CertManager for cleaning up on unregister.

    This class should not need a consumer id, or a uep connection, since it
    is running post unregister.
    """
    def _get_libset(self):

        self.entcertlib = EntCertActionInvoker()
        self.repolib = RepoActionInvoker()

        lib_set = [self.entcertlib, self.repolib]
        return lib_set
