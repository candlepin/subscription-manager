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
from subscription_manager.certlib import CertLib, ActionLock, HealingLib, IdentityCertLib
from subscription_manager.factlib import FactLib
from subscription_manager.repolib import RepoLib
from subscription_manager.brandlib import BrandLib

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


class CertManager:
    """
    An object used to update the certficates, yum repos, and facts for
    the system.

    @ivar certlib: The RHSM I{entitlement} certificate management lib.
    @type certlib: L{CertLib}
    @ivar repolib: The RHSM repository management lib.
    @type repolib: L{RepoLib}
    """

    def __init__(self, lock=ActionLock(), uep=None, product_dir=None,
            facts=None):
        self.lock = lock
        self.uep = uep
        self.certlib = CertLib(self.lock, uep=self.uep)
        self.repolib = RepoLib(self.lock, uep=self.uep)
        self.factlib = FactLib(self.lock, uep=self.uep, facts=facts)
        self.profilelib = PackageProfileLib(self.lock, uep=self.uep)
        self.installedprodlib = InstalledProductsLib(self.lock, uep=self.uep)
        #healinglib requires a fact set in order to get socket count
        self.healinglib = HealingLib(self.lock, self.uep, product_dir)
        self.idcertlib = IdentityCertLib(self.lock, uep=self.uep)
        self.brandlib = BrandLib(self.lock, uep=self.uep, product_dir)

    def update(self, autoheal=False):
        """
        Update I{entitlement} certificates and corresponding
        yum repositiories.
        @return: The number of updates required.
        @rtype: int
        """
        updates = 0
        lock = self.lock
        try:
            lock.acquire()

            # WARNING: order is important here, we need to update a number
            # of things before attempting to autoheal, and we need to autoheal
            # before attempting to fetch our certificates:
            if autoheal:
                libset = [self.installedprodlib, self.healinglib]
            else:
                libset = [self.idcertlib, self.repolib, self.factlib, self.profilelib, self.installedprodlib]

            # WARNING
            # Certlib inherits DataLib as well as the above 'lib' objects,
            # but for some reason it's update method returns a tuple instead
            # of an int:
            ret = []
            try:
                ret = self.certlib.update()
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

            # run the certlib update first as it will talk to candlepin,
            # and we can find out if we got deleted or not.
            for lib in libset:
                try:
                    updates += lib.update()
                except GoneException, e:
                    raise
                # raise this so it can be exposed clearly
                except ExpiredIdentityCertException, e:
                    raise
                except Exception, e:
                    log.warning("Exception caught while running %s update" % lib)
                    log.exception(e)

            # NOTE: with no consumer cert, most of these actually
            # fail
            if ret:
                updates += ret[0]
                for e in ret[1]:
                    print ' '.join(str(e).split('-')[1:]).strip()

        finally:
            lock.release()
        return updates
