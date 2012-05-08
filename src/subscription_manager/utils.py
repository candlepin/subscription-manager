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
from constants import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME
from urlparse import urlparse

log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)
gettext.textdomain("rhsm")


def remove_scheme(uri):
    """Remove the scheme component from a URI."""
    return re.sub("^[A-Za-z][A-Za-z0-9+-.]*://", "", uri)


class ServerUrlParseError(Exception):
    def __init__(self, serverurl, msg=None):
        self.serverurl = serverurl
        self.msg = msg


class ServerUrlParseErrorEmpty(ServerUrlParseError):
    pass


class ServerUrlParseErrorNone(ServerUrlParseError):
    pass


class ServerUrlParseErrorPort(ServerUrlParseError):
    pass


class ServerUrlParseErrorPath(ServerUrlParseError):
    pass


class ServerUrlParseErrorScheme(ServerUrlParseError):
    pass


class ServerUrlParseErrorSchemeNoDoubleSlash(ServerUrlParseError):
    pass


class ServerUrlParseErrorJustScheme(ServerUrlParseError):
    pass


def parse_server_info(local_server_entry):
    """
    Parse hostname, port, and webapp prefix from the string a user entered.

    Expected format: hostname:port/prefix

    Port and prefix are optional.
    """
    # Adding http:// onto the front of the hostname

    if local_server_entry == "":
        raise ServerUrlParseErrorEmpty(local_server_entry,
                                       msg=_("Server URL can not be empty"))

    if local_server_entry is None:
        raise ServerUrlParseErrorNone(local_server_entry,
                                      msg=_("Server URL can not be None"))

    # do we seem to have a scheme?
    if local_server_entry.find("://") > -1:

        # doh, but not one we want
        if (local_server_entry[:7] != "http://") and (local_server_entry[:8] != "https://"):
            raise ServerUrlParseErrorScheme(local_server_entry,
                msg=_("Server URL has an invalid scheme. http:// and https:// are supported"))

        # just the scheme? really?
        elif local_server_entry.split('://')[1] == '':
            raise ServerUrlParseErrorJustScheme(local_server_entry,
                msg=_("Server URL is just a schema. Should include hostname, and/or port and path"))

        # seem to have a workable schema already
        else:
            url = local_server_entry

    # try to detect "http:/hostname"
    elif len(local_server_entry.split(':/')) > 1:
        # if we only have 'http:/dfsd' and we split on
        # ':/' we end up with [0]='http'
        # and [1] = "hostname"
        # but for "http://hostname" we end up with [1] like
        # "/hostname", so check for that
        split_url = local_server_entry.split(':/')

        # verify this is an attempt at http://
        if split_url[0].startswith('http'):
            if not split_url[1].startswith('/'):
                raise ServerUrlParseErrorSchemeNoDoubleSlash(local_server_entry,
                    msg=_("Server URL has an invalid scheme (no //?)"))

        # else is just a url with no scheme and  ':/' in it somewhere
        url = "https://%s" % local_server_entry
    else:
        # append https scheme
        url = "https://%s" % local_server_entry

    #FIXME: need a try except here? docs
    # don't seem to indicate any expected exceptions
    result = urlparse(url)

    # in some cases, if we try the attr accessors, we'll
    # get a ValueError deep down in urlparse, particular if
    # port ends up being None
    #
    # So maybe check result.port/path/hostname for None, and
    # throw an exception in those cases.
    # adding the schem seems to avoid this though
    port = DEFAULT_PORT
    try:
        if result.port is not None:
            port = str(result.port)
    except ValueError:
        raise ServerUrlParseErrorPort(local_server_entry,
                                      msg=_("Server url port could not be parsed"))

    # path can be None?
    prefix = DEFAULT_PREFIX
    if result.path is not None:
        if result.path != '':
            prefix = result.path

    hostname = DEFAULT_HOSTNAME
    if result.hostname is not None:
        if result.hostname != "":
            hostname = result.hostname

    return (hostname, port, prefix)
