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

from subscription_manager.cache import PackageProfileLib, InstalledProductsLib
from subscription_manager.certlib import EntCertLib, HealingLib, IdentityCertLib
from subscription_manager.factlib import FactLib
from subscription_manager.repolib import RepoLib
from subscription_manager import injection as inj

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


class BaseCertManager:
    """
    An object used to update the certficates, yum repos, and facts for the system.
    """

    # can we inject both of these?
    def __init__(self, uep=None, facts=None):

        # inject?
        self.uep = uep
        self.facts = facts

        self._libset = self._get_libset()
        self.lock = inj.require(inj.ACTION_LOCK)
        self.report = None

    def _get_libset(self):
        return []

    def update(self, autoheal=False):
        """
        Update I{entitlement} certificates and corresponding
        yum repositiories.
        @return: A list of update reports
        @rtype: list
        """
        # dict of certlib->report?
        update_reports = []
        lock = self.lock
        try:
            lock.acquire()
            update_reports = self._run_updates(autoheal)
        finally:
            lock.release()

        # updates at this point is a int representing how many
        # things were updated, which is pretty much completely useless
        print "update reports: ", update_reports
        return update_reports

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
            log.warning("Exception caught while running certlib update")
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


class CertManager(BaseCertManager):

    def _get_libset(self):

        self.entcertlib = EntCertLib(uep=self.uep)
        self.repolib = RepoLib(uep=self.uep)
        self.factlib = FactLib(uep=self.uep, facts=self.facts)
        self.profilelib = PackageProfileLib(uep=self.uep)
        self.installedprodlib = InstalledProductsLib(uep=self.uep)
        self.healinglib = HealingLib(self.uep)
        self.idcertlib = IdentityCertLib(uep=self.uep)

        # WARNING: order is important here, we need to update a number
        # of things before attempting to autoheal, and we need to autoheal
        # before attempting to fetch our certificates:
        lib_set = [self.entcertlib, self.idcertlib, self.repolib,
                   self.factlib, self.profilelib,
                   self.installedprodlib]

        return lib_set


class HealingCertManager(BaseCertManager):
    def _get_libset(self):

        self.entcertlib = EntCertLib(uep=self.uep)
        self.installedprodlib = InstalledProductsLib(uep=self.uep)
        self.healinglib = HealingLib(self.uep)

        # FIXME: note this runs entcertlib twice, once to make sure we are
        # setup, then again after heal to get any additional certs. We may be
        # able to avoid that by conditionally calling entcertlib from within
        # healinglib (as we did before)
        lib_set = [self.entcertlib, self.installedprodlib, self.healinglib, self.entcertlib]

        return lib_set
