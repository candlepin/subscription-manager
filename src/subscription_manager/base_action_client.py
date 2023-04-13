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
from typing import List, Optional, TYPE_CHECKING

from rhsm.connection import GoneException, ExpiredIdentityCertException

from subscription_manager import injection as inj

if TYPE_CHECKING:
    from subscription_manager.certlib import BaseActionInvoker, ActionReport
    from subscription_manager.lock import ActionLock

log = logging.getLogger(__name__)


class BaseActionClient:
    """
    An object used to update the certificates, DNF repos, and facts for the system.
    """

    def __init__(self, skips: List[type("ActionReport")] = None):
        self._libset: List[BaseActionInvoker] = self._get_libset()
        self.lock: ActionLock = inj.require(inj.ACTION_LOCK)
        self.update_reports: List[ActionReport] = []
        self.skips: List[type(ActionReport)] = skips or []

    def _get_libset(self) -> List["BaseActionInvoker"]:
        # FIXME (?) Raise NotImplementedError, to ensure each subclass is using its own function
        return []

    def update(self) -> None:
        """
        Update entitlement certificates and corresponding DNF repositories.
        """
        # TODO: move to using a lock context manager
        try:
            self.lock.acquire()
            self.update_reports = self._run_updates()
        finally:
            self.lock.release()

    def _run_update(self, lib: "BaseActionInvoker") -> "ActionReport":
        update_report: Optional[ActionReport] = None

        try:
            update_report = lib.update()
        # see bz#852706, reraise GoneException so that consumer cert deletion works
        except GoneException:
            raise
        # raise this so it can be exposed clearly
        except ExpiredIdentityCertException:
            raise
        except Exception as e:
            log.warning("Exception caught while running %s update" % lib)
            log.exception(e)

        if update_report:
            update_report.print_exceptions()

        return update_report

    def _run_updates(self) -> List["ActionReport"]:
        update_reports: List[ActionReport] = []

        for lib in self._libset:
            if type(lib) in self.skips:
                continue

            log.debug("running lib: %s" % lib)
            update_report: ActionReport = self._run_update(lib)

            # a map/dict may make more sense here
            update_reports.append(update_report)

        return update_reports
