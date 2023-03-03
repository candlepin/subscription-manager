import logging
from typing import Any, Callable, Optional, List, Union, TYPE_CHECKING

from subscription_manager import injection as inj

if TYPE_CHECKING:
    from subscription_manager.lock import ActionLock

log = logging.getLogger(__name__)


class Locker:
    def __init__(self):
        self.lock: ActionLock = self._get_lock()

    def run(self, action: Callable) -> Any:
        self.lock.acquire()
        try:
            return action()
        finally:
            self.lock.release()

    def _get_lock(self) -> "ActionLock":
        return inj.require(inj.ACTION_LOCK)


class BaseActionInvoker:
    def __init__(self, locker: Optional[Locker] = None):
        self.locker = locker or Locker()
        self.report: Any = None
        """Output of the callable"""

    def update(self) -> Any:
        self.report = self.locker.run(self._do_update)
        return self.report

    def _do_update(self):
        """Thing the "lib" needs to do"""
        return


class ActionReport:
    """Base class for cert lib and action reports"""

    name: str = "Report"

    def __init__(self):
        self._status: Optional[str] = None
        self._exceptions: List[Union[Exception, str]] = []
        self._updates: List[str] = []

    def log_entry(self) -> None:
        """log report entries"""

        # assuming a useful repr
        log.debug(self)

    def format_exceptions(self) -> str:
        buf: str = ""
        for e in self._exceptions:
            buf += str(e).split("-", maxsplit=1)[-1].strip()
            buf += "\n"
        return buf

    def print_exceptions(self) -> None:
        if self._exceptions:
            print(self.format_exceptions())

    def __str__(self) -> str:
        template: str = """%(report_name)s
        status: %(status)s
        updates: %(updates)s
        exceptions: %(exceptions)s
        """
        return template % {
            "report_name": self.name,
            "status": self._status,
            "updates": self._updates,
            "exceptions": self.format_exceptions(),
        }
