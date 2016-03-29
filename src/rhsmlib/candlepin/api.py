import logging
import socket
from M2Crypto import SSL

import rhsm.connection

log = logging.getLogger(__name__)


# Likely needs to subclass RestlibException etc
class CandlepinApiError(Exception):
    pass


class CandlepinApiSSLError(CandlepinApiError):
    pass


class CandlepinApiRestlibError(CandlepinApiError):
    pass


class CandlepinApiAuthenticationError(CandlepinApiError):
    pass


class CandlepinApiExpiredIDCertError(CandlepinApiError):
    pass


class CandlepinApiNetworkError(CandlepinApiError):
    pass


class Candlepin(object):
    def __init__(self, uep):
        self.uep = uep
        self._default_args = ()
        self.last_error = None

    @property
    def default_args(self):
        # could include the default success/error callbacks
        return self._default_args

    @property
    def default_kwargs(self):
        return self._default_kwargs

    def call(self, rest_method, *args, **kwargs):
        success_callback = None
        error_callback = None
        if 'success_callback' in kwargs:
            success_callback = kwargs['success_callback']
        if 'error_callback' in kwargs:
            error_callback = kwargs['error_callback']

        log.debug('success_cb=%s', success_callback)
        log.debug('error_callback=%s', error_callback)
        log.debug('rest_method=%s %s', rest_method, type(rest_method))

        try:
            args = self.default_args + args
            return rest_method(*args, **kwargs)
        except AttributeError as e:
            log.exception(e)
            raise
        except SSL.SSLError as ex:
            log.exception(ex)
            self.last_error = ex
            log.error("Consumer certificate is invalid")
            # FIXME: we can get the consumer identity here, and point to the uuid/cert
            raise CandlepinApiSSLError('SSL related error (consumer identity cert is invalid?): %s' % ex)
        except rhsm.connection.RestlibException as ex:
            # Indicates we may be talking to a very old candlepin server
            # which does not have the necessary API call.
            log.exception(ex)
            self.last_error = ex
            raise CandlepinApiRestlibError('Error from candlepin: %s' % ex)
        except rhsm.connection.AuthenticationException as ex:
            log.error("Could not authenticate with server, check registration status.")
            log.exception(ex)
            self.last_error = ex
            raise CandlepinApiAuthenticationError("Could not authenticate with server, check registration status.: %s" % ex)
        except rhsm.connection.ExpiredIdentityCertException as ex:
            log.exception(ex)
            self.last_error = ex
            msg = "Bad identity, unable to connect to server"
            raise CandlepinApiExpiredIDCertError("%s: %s" % (msg, ex))
        except rhsm.connection.GoneException:
            raise
        # Most of the above are subclasses of ConnectionException that
        # get handled first
        except (rhsm.connection.ConnectionException,
                socket.error) as ex:

            log.error(ex)
            self.last_error = ex

            msg = "Unable to reach server, using cached status."
            log.warn(msg)
            raise CandlepinApiNetworkError('%s: %s' % (msg, ex))


class CandlepinConsumer(Candlepin):
    def __init__(self, uep, uuid):
        self.uep = uep
        self.uuid = uuid
        self._default_args = (self.uuid,)
