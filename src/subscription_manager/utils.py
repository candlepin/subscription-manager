#
# Copyright (c) 2012 Red Hat, Inc.
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

import re
import logging
from constants import DEFAULT_PORT, DEFAULT_PREFIX
from urlparse import urlparse

log = logging.getLogger('rhsm-app.' + __name__)


def remove_scheme(uri):
    """Remove the scheme component from a URI."""
    return re.sub("^[A-Za-z][A-Za-z0-9+-.]*://", "", uri)

def parse_server_info(local_server_entry):
    """
    Parse hostname, port, and webapp prefix from the string a user entered.

    Expected format: hostname:port/prefix

    Port and prefix are optional.
    """
    # Adding http:// onto the front of the hostname

    url = 'http://%s' % local_server_entry
    result = urlparse(url)

    port = DEFAULT_PORT
    #foo = result.port
    #print foo
    if result.port is not None:
        port = str(result.port)

    prefix = DEFAULT_PREFIX
    if result.path != '':
        prefix = result.path

    return (result.hostname, port, prefix)

