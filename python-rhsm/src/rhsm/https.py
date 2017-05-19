from __future__ import print_function, division, absolute_import

# A compatibility wrapper that provides httplib and ssl using either standard libs or m2crypto.
#
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
import ssl as _ssl
import os

log = logging.getLogger(__name__)

_SSL_REQUIRED_FEATURES = [
    'SSLContext',
    'CERT_NONE',
    'CERT_REQUIRED',
    'PROTOCOL_SSLv23',
    'OP_ALL',
    'OP_NO_SSLv2',
    'OP_NO_SSLv3',
]

_SSL_CONTEXT_REQUIRED_FEATURES = [
    'check_hostname',
    'options',
    'verify_mode',
]

using_stdlibs = True
for _feature in _SSL_REQUIRED_FEATURES:
    if not hasattr(_ssl, _feature):
        using_stdlibs = False

if using_stdlibs:
    _SslContext = _ssl.SSLContext
    for _feature in _SSL_CONTEXT_REQUIRED_FEATURES:
        if not hasattr(_SslContext, _feature):
            using_stdlibs = False

if 'RHSM_USE_M2CRYPTO' in os.environ:
    using_stdlibs = os.environ['RHSM_USE_M2CRYPTO'].lower() not in ['true', '1', 'yes']

if using_stdlibs:
    log.debug('Using standard libs to provide httplib and ssl')
    import six.moves.http_client as _httplib
    ssl = _ssl
    httplib = _httplib
else:
    log.debug('Using m2crypto wrappers to provide httplib and ssl')
    import rhsm.m2cryptossl
    import rhsm.m2cryptohttp
    ssl = rhsm.m2cryptossl
    httplib = rhsm.m2cryptohttp
