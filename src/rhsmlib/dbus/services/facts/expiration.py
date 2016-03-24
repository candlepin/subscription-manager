import logging

import datetime

log = logging.getLogger(__name__)


class Expiration(object):
    """FactsCollections can potentially expire. If so, Expiration decides when."""
    default_seconds = 0
    never_expire = True

    def __init__(self, start_datetime=None, duration_seconds=None):
        """start_datetime is the expirations start, duration_seconds is length of lifetime in seconds.

        Passing a duration_seconds of None means no expiration, and expired()
        will never return True.

        If duration_seconds is 0 or negative, expired() will always return True."""
        self.start_datetime = start_datetime or datetime.datetime.utcnow()

        if duration_seconds is None:
            self.never_expire = True
            seconds = self.default_seconds
        else:
            self.never_expire = False
            seconds = duration_seconds

        self.duration = datetime.timedelta(seconds=seconds)

    def expired(self, at_time=None):
        at_time = at_time or datetime.datetime.utcnow()
        log.debug("Self=%s", self)
        log.debug("FC    expire check expdt=%s at_time=%s", repr(self.expiry_datetime), repr(at_time))
        log.debug("FC    expire check expdt=%s at_time=%s", self.expiry_datetime, at_time)
        log.debug("FC    expire check exp < at_time = %s", self.expiry_datetime < at_time)
        return self.expiry_datetime < at_time

    @property
    def expiry_datetime(self):
        #log.debug("expiry_datetime")
        return self.start_datetime + self.duration
