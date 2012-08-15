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
from rhsm.config import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME, \
    DEFAULT_CDN_HOSTNAME, DEFAULT_CDN_PORT, DEFAULT_CDN_PREFIX
from urlparse import urlparse
import os
import signal

log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)
gettext.textdomain("rhsm")

from rhsm.connection import UEPConnection, RestlibException, GoneException
from subscription_manager.hwprobe import ClassicCheck
from rhsm.version import Versions
from M2Crypto.SSL import SSLError


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


def parse_server_info(local_server_entry):
    return parse_url(local_server_entry,
                     DEFAULT_HOSTNAME,
                     DEFAULT_PORT,
                     DEFAULT_PREFIX)


def parse_baseurl_info(local_server_entry):
    return parse_url(local_server_entry,
                     DEFAULT_CDN_HOSTNAME,
                     DEFAULT_CDN_PORT,
                     DEFAULT_CDN_PREFIX)


def format_baseurl(hostname, port, prefix):
    # just to avoid double slashs. cosmetic
    if prefix and prefix[0] != '/':
        prefix = "/%s" % prefix

    # remove trailing slash, just so same
    # values as default matches default format
    if prefix == DEFAULT_CDN_PREFIX:
        prefix = prefix[:-1]

    # just so we match how we format this by
    # default
    if port == DEFAULT_CDN_PORT:
        return "https://%s%s" % (hostname,
                                  prefix)

    return "https://%s:%s%s" % (hostname,
                                 port,
                                 prefix)


def has_bad_scheme(url):
    bad_fragments = ["http//", "http/",
                     "https//", "https/"]
    short_fragments = [("http:", "http://"),
                       ("http:/", "http://"),
                       ("https:", "https://"),
                       ("https:/", "https://")]

    # we could in theory, have a host named 'http',
    # so that http/prefix is a valid url. However, do not
    # do that. If you have to, use http://http/blah.
    # Sorry.
    for bad_fragment in bad_fragments:
        if url.startswith(bad_fragment):
            return True

    # handle truncated schemes
    for short_fragment in short_fragments:
        if url.startswith(short_fragment[0]) and \
                not url.startswith(short_fragment[1]):
            return True

    # this could in theory be a local path, but that
    # doesn't really help us
    if url.startswith(':/'):
        return True

    # if we have a scheme, and we may not, make
    # sure it's valid
    url_split = url.split('://')
    if len(url_split) > 1:
        if url_split[0] not in ["http", "https"]:
            return True

    return False


def has_good_scheme(url):
    good_schemes = ["http", "https"]
    url_parts = url.split('://')
    if url_parts[0] not in good_schemes:
        return False

    # a good scheme alone is not really a good scheme
    if len(url_parts) > 1 and url_parts[1] == '':
        raise ServerUrlParseErrorJustScheme(url,
                msg=_("Server URL is just a schema. Should include hostname, and/or port and path"))
    return True


def parse_url(local_server_entry,
              default_hostname=None,
              default_port=None,
              default_prefix=None):
    """
    Parse hostname, port, and webapp prefix from the string a user entered.

    Expected format: hostname:port/prefix

    Port and prefix are optional.

    Returns:
        a tuple of (hostname, port, path)
    """
    # Adding http:// onto the front of the hostname

    if local_server_entry == "":
        raise ServerUrlParseErrorEmpty(local_server_entry,
                                       msg=_("Server URL can not be empty"))

    if local_server_entry is None:
        raise ServerUrlParseErrorNone(local_server_entry,
                                      msg=_("Server URL can not be None"))

    # good_url in this case meaning a schema we support, and
    # _something_ else. This is to make urlparse happy
    good_url = None

    # handle any known or troublesome or bogus typo's, etc
    if has_bad_scheme(local_server_entry):
        raise ServerUrlParseErrorScheme(local_server_entry,
            msg=_("Server URL has an invalid scheme. http:// and https:// are supported"))

    # we want to see if we have a good scheme, and
    # at least _something_ else
    if has_good_scheme(local_server_entry):
        good_url = local_server_entry

    # not having a good scheme could just mean we don't have a scheme,
    # so let's include one so urlparse doesn't freak
    if not good_url:
        good_url = "https://%s" % local_server_entry

    #FIXME: need a try except here? docs
    # don't seem to indicate any expected exceptions
    result = urlparse(good_url)
    netloc = result[1].split(":")

    # in some cases, if we try the attr accessors, we'll
    # get a ValueError deep down in urlparse, particular if
    # port ends up being None
    #
    # So maybe check result.port/path/hostname for None, and
    # throw an exception in those cases.
    # adding the schem seems to avoid this though
    port = default_port
    if len(netloc) > 1:
        if netloc[1] != "":
            port = str(netloc[1])
        else:
            raise ServerUrlParseErrorPort(local_server_entry,
                                      msg=_("Server url port could not be parsed"))

    # path can be None?
    prefix = default_prefix
    if result[2] is not None:
        if result[2] != '':
            prefix = result[2]

    hostname = default_hostname
    if netloc[0] is not None:
        if netloc[0] != "":
            hostname = netloc[0]

    try:
        int(port)
    except ValueError:
        raise ServerUrlParseErrorPort(local_server_entry,
                                      msg=_("Server url port should be numeric"))

    return (hostname, port, prefix)


class MissingCaCertException(Exception):
    pass


# TODO: make sure this works with --proxy cli options
def is_valid_server_info(hostname, port, prefix):
    """
    Check if we can communicate with a subscription service at the given
    location.

    Returns true or false.

    May throw a MissingCaCertException if the CA certificate has not been
    imported yet, which may be relevant to the caller.
    """
    # Proxy info should already be in config file and used by default:
    try:
        conn = UEPConnection(host=hostname, ssl_port=int(port), handler=prefix)
        conn.ping()
        return True
    except RestlibException, e:
        # If we're getting Unauthorized that's a good indication this is a
        # valid subscription service:
        if e.code == 401:
            return True
        else:
            log.exception(e)
            return False
    except SSLError, e:
        # Indicates a missing CA certificate, which callers may need to
        # notify the user of:
        raise MissingCaCertException(e)
    except Exception, e:
        log.exception(e)
        return False


def get_version(versions, package_name):
    """
    Return a string containing the version (and release if available).
    """
    # If the version is not set assume it is not installed via RPM.
    package_version = versions.get_version(package_name)
    package_release = versions.get_release(package_name)
    if package_release:
        package_release = "-%s" % package_release
    return "%s%s" % (package_version, package_release)


def get_client_versions():
    # It's possible (though unlikely, and kind of broken) to have more
    # than one version of python-rhsm/subscription-manager installed.
    # Versions() will only return one (and I suspect it's not predictable
    # which it will return).
    versions = Versions()
    sm_version = get_version(versions, Versions.SUBSCRIPTION_MANAGER)
    pr_version = get_version(versions, Versions.PYTHON_RHSM)

    return {"subscription manager": sm_version,
            "python-rhsm": pr_version}


def get_server_versions(cp):
    cp_version = _("No connection made to remote entitlement server")
    server_type = _("Unknown")
    if cp:
        server_type = _("subscription management service")
        try:
            if cp.supports_resource("status"):
                status = cp.getStatus()
                cp_version = '-'.join([status['version'], status['release']])
            else:
                cp_version = _("Unknown")
        except GoneException, e:
            log.info(e)
            raise
        except Exception, e:
            # a more useful error would be handy here
            print _("Error while checking server version: %s") % e
            log.exception(e)

            server_type = _("Unknown")
            cp_version = _("Unknown")

    if ClassicCheck().is_registered_with_classic():
        server_type = _("RHN Classic")
        cp_version = _("Unknown")

    return {"candlepin": cp_version,
            "server-type": server_type}


def restart_virt_who():
    """
    Send a SIGHUP signal to virt-who if it running on the same machine.
    """
    try:
        pidfile = open('/var/run/virt-who.pid', 'r')
        pid = int(pidfile.read())
        os.kill(pid, signal.SIGHUP)
        log.debug("Restarted virt-who")
    except IOError:
        # The file was not found, this is ok
        log.debug("No virt-who pid file, no attempting to restart")
    except OSError:
        # The file is referencing an old pid, record this and move on
        log.error("There virt-who pid file references a non-existent pid")
    except ValueError:
        # The file has non numeric data in it
        log.error("There virt-who pid file contains non numeric data")
