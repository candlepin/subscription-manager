
import logging

# ugh, why does everything monkey patch this
# replace with identity injection
from subscription_manager.identity import ConsumerIdentity
from subscription_manager import injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class Locker(object):

    def __init__(self):
        self.lock = self._get_lock()

    def run(self, action):
        self.lock.acquire()
        try:
            return action()
        finally:
            self.lock.release()

    def _get_lock(self):
        return inj.require(inj.ACTION_LOCK)


class DataLib(object):
    def __init__(self, uep=None):
        self.locker = Locker()
        self.uep = uep
        self.report = None

    def update(self):
        self.report = self.locker.run(self._do_update)
        return self.report

    def _do_update(self):
        """Thing the "lib" needs to do"""
        return


class ActionReport(object):
    """Base class for cert lib and action reports"""
    name = "Report"

    def __init__(self):
        self._status = None
        self._exceptions = []
        self._updates = []

    def log_entry(self):
        """log report entries"""

        # assuming a useful repr
        log.info(self)

    def format_exceptions(self):
        buf = ''
        for e in self._exceptions:
            buf += ' '.join(str(e).split('-')[1:]).strip()
            buf += '\n'
        return buf

    def print_exceptions(self):
        if self._exceptions:
            print self.format_exceptions()

    def __str__(self):
        template = """%(report_name)s
        status: %(status)s
        updates: %(updates)s
        exceptions: %(exceptions)s
        """
        return template % {'report_name': self.name,
                           'status': self._status,
                           'updates': self._updates,
                           'exceptions': self.format_exceptions()}
