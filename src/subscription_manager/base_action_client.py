#
# Copyright (c) 2014 Red Hat, Inc.
#
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

from subscription_manager import injection as inj

from rhsm.connection import GoneException, ExpiredIdentityCertException

log = logging.getLogger(__name__)


class BaseActionClient(object):
    """
    An object used to update the certficates, yum repos, and facts for the system.
    """

    def __init__(self):

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
            log.debug("running lib: %s" % lib)
            update_report = self._run_update(lib)

            # a map/dict may make more sense here
            update_reports.append(update_report)

        return update_reports
