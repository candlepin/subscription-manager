from __future__ import print_function, division, absolute_import

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

import os
import re
import sys

import six.moves.urllib.parse

from rhsm.config import DEFAULT_PROXY_PORT


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


class ServerUrlParseErrorJustScheme(ServerUrlParseError):
    pass


class UnsupportedOperationException(Exception):
    """Thrown when a call is made that is unsupported in the current
    state.  For example, if a call is made to a deprecated API when
    a newer API is available.
    """
    pass


def has_bad_scheme(url):
    """Check a url for an invalid or unuseful schema.

    Don't allow urls to start with :/ http/ https/ non http/httpsm or http(s) with single /

    :params url: URL string to check
    :type url: str
    :returns: True if the url schme is "bad"
    :rtype: boolean
    """
    match_bad = '(https?[:/])|(:/)|(\S+://)'
    match_good = 'https?://'
    # Testing good first allows us to exclude some regex for bad
    if re.match(match_good, url):
        return False
    if re.match(match_bad, url):
        return True
    return False


def has_good_scheme(url):
    match = re.match("https?://(\S+)?", url)
    if not match:
        return False
    # a good scheme alone is not really a good scheme
    if not match.group(1):
        raise ServerUrlParseErrorJustScheme(url)
    return True


def parse_url(local_server_entry,
              default_hostname=None,
              default_port=None,
              default_prefix=None,
              default_username=None,
              default_password=None):
    """
    Parse hostname, port, and webapp prefix from the string a user entered.

    Expected format: username:password@hostname:port/prefix

    Username, password, port and prefix are optional.

    :param local_server_entry: URL of a candlepin server
    :type: str
    :param default_hostname: default_hostname
    :param default_port: default_port
    :return: a tuple of (username, password, hostname, port, path)
    """

    if local_server_entry == "":
        raise ServerUrlParseErrorEmpty(local_server_entry)

    if local_server_entry is None:
        raise ServerUrlParseErrorNone(local_server_entry)

    # good_url in this case meaning a schema we support, and
    # _something_ else. This is to make urlparse happy
    good_url = None

    # handle any known or troublesome or bogus typo's, etc
    if has_bad_scheme(local_server_entry):
        raise ServerUrlParseErrorScheme(local_server_entry)

    # we want to see if we have a good scheme, and
    # at least _something_ else
    if has_good_scheme(local_server_entry):
        good_url = local_server_entry

    # not having a good scheme could just mean we don't have a scheme,
    # so let's include one so urlparse doesn't freak
    if not good_url:
        good_url = "https://%s" % local_server_entry

    # FIXME: need a try except here? docs
    #        don't seem to indicate any expected exceptions
    result = six.moves.urllib.parse.urlparse(good_url)

    username = result.username
    if username is None or username == "":
        username = default_username

    password = result.password
    if password is None:
        password = default_password

    hostname = result.hostname
    if hostname is None:
        hostname = default_hostname

    try:
        port = result.port
    except ValueError:
        raise ServerUrlParseErrorPort(local_server_entry)

    if port is None:
        port = default_port
    else:
        port = str(port)

    prefix = result.path
    if prefix is None or prefix == "":
        prefix = default_prefix

    return username, password, hostname, port, prefix


def get_env_proxy_info():
    the_proxy = {'proxy_username': '',
                 'proxy_hostname': '',
                 'proxy_port': '',
                 'proxy_password': ''}

    # get the proxy information from the environment variable
    # if available
    # look in the following order:
    #   HTTPS_PROXY
    #   https_proxy
    #   HTTP_PROXY
    #   http_proxy
    # look through the list for the first one to match
    info = ()
    env_vars = ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"]
    for ev in env_vars:
        proxy_info = os.getenv(ev)
        if proxy_info:
            info = parse_url(proxy_info, default_port=DEFAULT_PROXY_PORT)
            break

    if info:
        the_proxy['proxy_username'] = info[0]
        the_proxy['proxy_password'] = info[1]
        the_proxy['proxy_hostname'] = info[2]
        if info[3] is None or info[3] == "":
            the_proxy['proxy_port'] = None
        else:
            the_proxy['proxy_port'] = int(info[3])
    return the_proxy


def cmd_name(argv):
    """Attempt to get a meaningful command name from argv.

    This handles cases where argv[0] isn't helpful (for
    example, '/usr/bin/python' or '__main__.py'.
    """
    argv0 = os.path.basename(argv[0])
    argvdir = os.path.dirname(argv[0])
    head, tail = os.path.split(argvdir)

    cmd_name_string = argv0
    # initial-setup is launched as 'python -m initial_setup', so
    # sys.argv looks like
    # ['/usr/lib/python2.7/site-packages/initial_setup/__main__.py'],
    # so we look for initial_setup in the exe path.
    if tail == "initial_setup":
        cmd_name_string = "initial-setup"

    return cmd_name_string


def fix_no_proxy():
    """
    This fixes no_proxy/NO_PROXY environment to not include leading
    asterisk, because there is some imperfection in proxy_bypass_environment.
    """

    # This fixes BZ: 1443164, because proxy_bypass_environment() from urllib does
    # not support no_proxy with items containing asterisk (e.g.: *.redhat.com)

    no_proxy = os.environ.get('no_proxy') or os.environ.get('NO_PROXY')
    if no_proxy is not None:
        if no_proxy != '*':
            # Remove all leading white spaces and asterisks from items of no_proxy
            # except item containing only "*" (urllib supports alone asterisk).
            no_proxy = ','.join([item.lstrip(' *') for item in no_proxy.split(',')])
            # Save no_proxy back to 'no_proxy' and 'NO_PROXY'
            os.environ['no_proxy'] = no_proxy
            os.environ['NO_PROXY'] = no_proxy


def suppress_output(func):
    def wrapper(*args, **kwargs):
        try:
            devnull = open(os.devnull, 'w')
            stdout = sys.stdout
            stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            return func(*args, **kwargs)
        finally:
            sys.stdout = stdout
            sys.stderr = stderr
            devnull.close()
    return wrapper
