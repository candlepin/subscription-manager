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

from certlib import CertLib, ActionLock
from repolib import RepoLib
from factlib import FactLib


class CertManager:
    """
    The RHSM certificate manager.
    @ivar certlib: The RHSM I{entitlement} certificate management lib.
    @type certlib: L{CertLib}
    @ivar repolib: The RHSM repository management lib.
    @type repolib: L{RepoLib}
    """

    def __init__(self, lock=ActionLock()):
        self.lock = lock
        self.certlib = CertLib(self.lock)
        self.repolib = RepoLib(self.lock)
        self.factlib = FactLib(self.lock)

    def add(self, *bundles):
        """
        Add I{entitlement} certificate bundles.
        Each I{bundle} is a dict {cert='',key=''}
        @param bundles: A certificate bundle.
        @type bundles: dict
        """
        lock = self.lock
        try:
            lock.acquire()
            self.certlib.add(*bundles)
            self.repolib.update()
        finally:
            lock.release()

    def update(self):
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
            for lib in (self.certlib, self.repolib, self.factlib):
                updates += lib.update()
        finally:
            lock.release()
        return updates


def main():
    print 'Updating Red Hat certificates & repositories'
    mgr = CertManager()
    updates = mgr.update()
    print '%d updates required' % updates
    print 'done'

if __name__ == '__main__':
    import logutil, sys
    log = logutil.getLogger(__name__)
    try:
        main()
    except Exception, e:
        log.error("Error while updating certificates using daemon")
        print 'Unable to update Red Hat certificates & repositories'
        log.exception(e)
        sys.exit(-1)
