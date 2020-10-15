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

# A compatibility wrapper that adapts m2crypto to the subset of standard
# lib ssl used in python-rhsm.

from M2Crypto import m2 as _m2, SSL as _ssl

CERT_NONE = _ssl.verify_none
CERT_REQUIRED = _ssl.verify_peer | _ssl.verify_fail_if_no_peer_cert
PROTOCOL_SSLv23 = 'sslv23'
OP_ALL = _m2.SSL_OP_ALL
OP_NO_SSLv2 = _m2.SSL_OP_NO_SSLv2
OP_NO_SSLv3 = _m2.SSL_OP_NO_SSLv3


class NoOpChecker(object):
    def __init__(self, host=None, peerCertHash=None, peerCertDigest='sha1'):
        self.host = host
        self.fingerprint = peerCertHash
        self.digest = peerCertDigest

    def __call__(self, peerCert, host=None):
        return True


class SSLContext(object):

    def __init__(self, version):
        self.m2context = _ssl.Context(version)
        self._options = None
        self._default_verify_depth = self.m2context.get_verify_depth()
        self.options = OP_ALL
        self.verify_mode = CERT_NONE
        self.check_hostname = False

    @property
    def check_hostname(self):
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, check_hostname):
        self._check_hostname = check_hostname
        if not check_hostname:
            self.m2context.post_connection_check = NoOpChecker()
        else:
            self.m2context.post_connection_check = None

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._options = options
        self.m2context.set_options(options)

    @property
    def verify_mode(self):
        return self.m2context.get_verify_mode()

    @verify_mode.setter
    def verify_mode(self, verify_mode):
        self.m2context.set_verify(verify_mode, self._default_verify_depth)

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        if cadata:
            raise NotImplementedError
        return self.m2context.load_verify_locations(cafile, capath)

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        if password:
            return self.m2context.load_cert(certfile, keyfile, lambda: password)
        else:
            return self.m2context.load_cert(certfile, keyfile)

SSLError = _ssl.SSLError
