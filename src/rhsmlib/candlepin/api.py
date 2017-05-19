from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
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
import socket
from rhsm.https import ssl

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
        success_callback = kwargs.get('success_callback', None)
        error_callback = kwargs.get('error_callback', None)

        log.debug('success_cb=%s', success_callback)
        log.debug('error_callback=%s', error_callback)
        log.debug('rest_method=%s %s', rest_method, type(rest_method))

        try:
            args = self.default_args + args
            return rest_method(*args, **kwargs)
        except AttributeError as e:
            log.exception(e)
            raise
        except ssl.SSLError as ex:
            log.exception(ex)
            self.last_error = ex
            log.error("Consumer certificate is invalid")
            raise CandlepinApiSSLError('SSL related error (consumer identity cert is invalid?): %s' % ex)
        except rhsm.connection.RestlibException as ex:
            # Indicates we may be talking to a very old candlepin server
            # which does not have the necessary API call.
            log.exception(ex)
            self.last_error = ex
            raise CandlepinApiRestlibError('Error from candlepin: %s' % ex)
        except rhsm.connection.AuthenticationException as ex:
            log.error("Could not authenticate with server. Check registration status.")
            log.exception(ex)
            self.last_error = ex
            raise CandlepinApiAuthenticationError("Could not authenticate with server. "
                  "Check registration status.: %s" % ex)
        except rhsm.connection.ExpiredIdentityCertException as ex:
            log.exception(ex)
            self.last_error = ex
            msg = "Bad identity, unable to connect to server"
            raise CandlepinApiExpiredIDCertError("%s: %s" % (msg, ex))
        except rhsm.connection.GoneException:
            raise
        # Most of the above are subclasses of ConnectionException that
        # get handled first
        except (rhsm.connection.ConnectionException, socket.error) as ex:
            log.error(ex)
            self.last_error = ex

            msg = "Unable to reach server."
            log.warn(msg)
            raise CandlepinApiNetworkError('%s: %s' % (msg, ex))


class CandlepinConsumer(Candlepin):
    def __init__(self, uep, uuid):
        self.uep = uep
        self.uuid = uuid
        self._default_args = (self.uuid,)
