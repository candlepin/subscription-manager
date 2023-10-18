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

import collections
import io
import logging
import os
import pprint
import re
import sys
import shutil
import signal
import socket
import syslog
import uuid
from typing import Callable, Dict, Iterable, Iterator, Optional, Tuple, TYPE_CHECKING

import urllib

from rhsm.https import ssl

from subscription_manager.branding import get_branding
from subscription_manager.certdirectory import Path
from rhsmlib.facts.hwprobe import ClassicCheck
from subscription_manager import injection as inj

# we moved quite a bit of code from this module to rhsm.
# we may want to import some of the other items for
# compatibility.
from rhsm.utils import parse_url
from rhsm.connection import ProxyException, ConnectionOSErrorException

import subscription_manager.version
from rhsm.connection import RestlibException, GoneException
from rhsm.config import (
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DEFAULT_HOSTNAME,
    DEFAULT_CDN_HOSTNAME,
    DEFAULT_CDN_PORT,
    DEFAULT_CDN_PREFIX,
)

from subscription_manager.i18n import ugettext as _

if TYPE_CHECKING:
    from rhsm.certificate2 import EntitlementCertificate
    from rhsm.connection import UEPConnection

    from rhsmlib.services import config as rhsmlib_config

    from subscription_manager.cache import CurrentOwnerCache, SupportedResourcesCache
    from subscription_manager.identity import Identity
    from subscription_manager.cp_provider import CPProvider

log = logging.getLogger(__name__)


VIRT_WHO_PID_FILES = ["/var/run/virt-who.pid", "/run/virt-who.pid"]


class DefaultDict(collections.defaultdict):
    """defaultdict wrapper that pretty prints"""

    def as_dict(self) -> dict:
        return dict(self)

    def __repr__(self) -> str:
        return pprint.pformat(self.as_dict())


def parse_server_info(
    local_server_entry: str, config: Optional["rhsmlib_config.Config"] = None
) -> Tuple[str, str, str]:
    hostname = ""
    port = ""
    prefix = ""
    if config is not None:
        hostname = config["server"]["hostname"]
        port = config["server"]["port"]
        prefix = config["server"]["prefix"]
    return parse_url(
        local_server_entry,
        hostname or DEFAULT_HOSTNAME,
        port or DEFAULT_PORT,
        prefix or DEFAULT_PREFIX,
    )[2:]


def parse_baseurl_info(local_server_entry: str) -> Tuple[str, str, str]:
    return parse_url(
        local_server_entry,
        DEFAULT_CDN_HOSTNAME,
        DEFAULT_CDN_PORT,
        DEFAULT_CDN_PREFIX,
    )[2:]


def format_baseurl(hostname: str, port: str, prefix: str) -> str:
    # just to avoid double slashs. cosmetic
    if prefix and prefix[0] != "/":
        prefix = "/%s" % prefix

    # remove trailing slash, just so same
    # values as default matches default format
    if prefix == DEFAULT_CDN_PREFIX:
        prefix = prefix[:-1]

    # Handle raw IPv6 addresses.
    # RFC 1035 only allows characters `a-zA-Z0-9.`, we can do this.
    if ":" in hostname:
        hostname = f"[{hostname}]"

    # just so we match how we format this by
    # default
    if port == DEFAULT_CDN_PORT:
        return "https://%s%s" % (hostname, prefix)

    return "https://%s:%s%s" % (hostname, port, prefix)


def url_base_join(base: str, url: str) -> str:
    """Join a baseurl (hostname) and url (full or relpath).

    If url is a full url, just return it. Otherwise combine
    it with base, skipping redundant separators if needed."""

    # I don't really understand this. Why does joining something
    # potentially non-empty and "" return ""? -akl
    if len(url) == 0:
        return url
    elif "://" in url:
        return url
    else:
        if base and (not base.endswith("/")):
            base = base + "/"
        if url and (url.startswith("/")):
            url = url.lstrip("/")
        return urllib.parse.urljoin(base, url)


class MissingCaCertException(Exception):
    pass


def is_valid_server_info(conn: "UEPConnection") -> bool:
    """
    Check if we can communicate with a subscription service at the given
    location.

    Returns true or false.

    May throw a MissingCaCertException if the CA certificate has not been
    imported yet, which may be relevant to the caller.
    """
    try:
        conn.ping()
        return True
    except RestlibException as e:
        # If we're getting Unauthorized that's a good indication this is a
        # valid subscription service:
        if e.code == 401:
            return True
        else:
            log.exception(e)
            return False
    except ssl.SSLError as e:
        # Indicates a missing CA certificate, which callers may need to
        # notify the user of:
        raise MissingCaCertException(e)
    except (ProxyException, ConnectionOSErrorException):
        raise
    except Exception as e:
        log.exception(e)
        return False


def is_simple_content_access(
    uep: Optional["UEPConnection"] = None, identity: Optional["Identity"] = None
) -> bool:
    """
    This function returns True, when current owner uses contentAccessMode equal to Simple Content Access.
    This function has three optional arguments that can be reused for getting required information.
    :param uep: connection to candlepin server
    :param identity: reference on current identity
    :return: True, when current owner uses contentAccesMode equal to org_environment. False otherwise.
    """
    if identity is None:
        identity = inj.require(inj.IDENTITY)

    # When identity is not known, then system is not registered
    if identity.uuid is None:
        return False
    content_access_mode = inj.require(inj.CONTENT_ACCESS_MODE_CACHE).read_data(uep=uep)
    return content_access_mode == "org_environment"


def get_current_owner(uep: Optional["UEPConnection"] = None, identity: "Identity" = None) -> dict:
    """
    This function tries to get information about current owner. It uses cache file.
    :param uep: connection to candlepin server
    :param identity: current identity of registered system
    :return: information about current owner
    """

    cache: CurrentOwnerCache = inj.require(inj.CURRENT_OWNER_CACHE)
    return cache.read_data(uep, identity)


def get_supported_resources(
    uep: Optional["UEPConnection"] = None, identity: Optional["Identity"] = None
) -> dict:
    """
    This function tries to get list of supported resources. It tries to use cache file.
    When the system is not registered, then it tries to get version directly using REST API.
    It is preferred to use this function instead of connection.get_supported_resources.
    :param uep: connection of candlepin server
    :param identity: current identity of registered system
    :return: list of supported resources
    """

    # Try to read supported resources from cache file
    if identity is not None:
        cache: SupportedResourcesCache = inj.require(inj.SUPPORTED_RESOURCES_CACHE)
        return cache.read_data(uep, identity)
    else:
        if uep is None:
            cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
            uep: UEPConnection = cp_provider.get_consumer_auth_cp()
        return uep.get_supported_resources()


def get_version(versions, package_name: str) -> str:
    """
    Return a string containing the version (and release if available).
    """
    # If the version is not set assume it is not installed via RPM.
    package_version = versions.get_version(package_name)
    package_release = versions.get_release(package_name)
    if package_release:
        package_release = "-%s" % package_release
    return "%s%s" % (package_version, package_release)


def get_terminal_width() -> Optional[int]:
    """
    Attempt to determine the current terminal size.
    """
    if not sys.stdout.isatty():
        return None
    dim = shutil.get_terminal_size(fallback=(None, None))
    if dim.columns is not None:
        return dim.columns
    else:
        # This allows tests to run
        return 1000


def get_client_versions() -> Dict[str, str]:
    # It's possible (though unlikely, and kind of broken) to have more
    # than one version of subscription-manager installed.
    # This will return whatever version we are using.
    sm_version = _("Unknown")

    try:
        sm_version = subscription_manager.version.pkg_version
        if sm_version is None or sm_version == "None":
            import pkg_resources

            sm_version = pkg_resources.require("subscription-manager")[0].version
    except Exception as e:
        log.debug("Client Versions: Unable to check client versions")
        log.exception(e)

    return {"subscription-manager": sm_version}


def get_server_versions(cp: "UEPConnection", exception_on_timeout: bool = False) -> Dict[str, str]:
    cp_version = _("Unknown")
    server_type = _("This system is currently not registered.")
    rules_version = _("Unknown")

    identity = inj.require(inj.IDENTITY)

    # check for Classic before doing anything else
    if ClassicCheck().is_registered_with_classic():
        if identity.is_valid():
            server_type = get_branding().REGISTERED_TO_BOTH_SUMMARY
        else:
            server_type = get_branding().REGISTERED_TO_OTHER_SUMMARY
    else:
        if identity.is_valid():
            server_type = get_branding().REGISTERED_TO_SUBSCRIPTION_MANAGEMENT_SUMMARY

    if cp:
        try:
            supported_resources = get_supported_resources(uep=cp)
            if "status" in supported_resources:
                status = cp.getStatus()
                cp_version = "-".join(
                    [status.get("version", _("Unknown")), status.get("release", _("Unknown"))]
                )
                rules_version = status.get("rulesVersion", _("Unknown"))
        except socket.timeout as e:
            log.error("Timeout error while checking server version")
            log.exception(e)
            # for cli, we can assume if we get a timeout here, the rest
            # of the calls will timeout as well, so raise exception here
            # instead of waiting for all the calls to timeout
            if exception_on_timeout:
                log.error("Timeout error while checking server version")
                raise
            # otherwise, ignore the timeout exception
        except Exception as e:
            if isinstance(e, GoneException):
                log.warn("Server Versions: Error: consumer has been deleted, unable to check server version")
            else:
                # a more useful error would be handy here
                log.error("Error while checking server version: %s" % e)

            log.exception(e)
            cp_version = _("Unknown")

    return {"candlepin": cp_version, "server-type": server_type, "rules-version": rules_version}


def restart_virt_who() -> None:
    """
    Send a SIGHUP signal to virt-who if it is running on the same machine.
    """

    # virt-who PID file can be in /var/run or /run directory
    virt_who_pid_file_name = None
    for pid_file_name in VIRT_WHO_PID_FILES:
        if os.path.isfile(pid_file_name):
            virt_who_pid_file_name = pid_file_name

    if virt_who_pid_file_name is None:
        log.debug("No virt-who pid file, not attempting to restart")
        return

    try:
        with open(virt_who_pid_file_name, "r") as pid_file:
            pid = int(pid_file.read())
        log.debug("Restarted virt-who")
    except IOError:
        # The file was not found, this is ok
        log.debug("Unable to read virt-who pid file, not attempting to restart")
    except ValueError:
        # The file has non numeric data in it
        log.error("The virt-who pid file contains non numeric data")
    else:
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError:
            # The file is referencing an old pid, record this and move on
            log.error("The virt-who pid file references a non-existent pid: %s", pid)


def friendly_join(items: Iterable[str]) -> str:
    if items is None:
        return ""

    items = [str(x) for x in items if x is not None]

    if not items:
        return ""

    if len(items) == 1:
        return items[0]

    first = items[0:-1]
    last = items[-1]
    first_string = ", ".join(first)

    if len(items) > 2:
        first_string = first_string + ","

    # FIXME: This is wrong in most non english locales.
    return first_string + " %s " % _("and") + last


def is_true_value(test_string) -> bool:
    val = str(test_string).lower()
    return val == "1" or val == "true" or val == "yes"


def system_log(message: str, priority: int = syslog.LOG_NOTICE):
    syslog.openlog("subscription-manager")
    syslog.syslog(priority, message)


def chroot(dirname: str) -> None:
    """
    Change root of all paths.
    """
    Path.ROOT = dirname


class CertificateFilter:
    def match(self, cert: "EntitlementCertificate"):
        """
        Checks if the specified certificate matches this filter's restrictions.
        Returns True if the specified certificate matches this filter's restrictions ; False
        otherwise.
        """
        raise NotImplementedError


class ProductCertificateFilter(CertificateFilter):
    def __init__(self, filter_string=None):
        super(ProductCertificateFilter, self).__init__()

        self._fs_regex = None

        if filter_string is not None:
            self.set_filter_string(filter_string)

    def set_filter_string(self, filter_string: Optional[str]) -> bool:
        """
        Sets this filter's filter string to the specified string. The filter string may use ? or *
        for wildcards, representing one or any characters, respectively.

        Returns True if the specified filter string was processed and assigned successfully; False
        otherwise.
        """
        literals = []
        wildcards = []
        translated = []
        output = False

        wildcard_map = {
            "*": ".*",
            "?": ".",
        }

        expression = """
            ((?:                # A captured, non-capture group :)
                [^*?\\\\]*        # Character literals and other uninteresting junk (greedy)
                (?:\\\\.?)*       # Anything escaped with a backslash, or just a trailing backslash
            )*)                 # Repeat the above sequence 0+ times, greedily
            ([*?]|\\Z)           # Any of our wildcards (* or ?) not preceded by a backslash OR end of input
        """

        if filter_string is not None:
            try:
                # Break it up based on our special characters...
                for match in re.finditer(expression, filter_string, re.VERBOSE):
                    literals.append(match.group(1))

                    if match.group(2):
                        wildcards.append(match.group(2))

                # ...and put it all back together.
                for literal in literals:
                    # Impl note:
                    # Unfortunately we need to unescape the literals so they can be safely re-escaped by the
                    # re.escape method; lest we risk doubly-escaping some stuff and breaking our regex
                    # horribly.
                    literal = re.sub(r"\\([*?\\])", r"\1", literal)
                    literal = re.escape(literal)

                    translated.append(literal)
                    if len(wildcards):
                        translated.append(wildcard_map.get(wildcards.pop(0)))

                self._fs_regex = re.compile("^%s$" % "".join(translated), re.IGNORECASE)
                output = True
            except TypeError:
                # Invalid filter string type. Rethrow with a proper message and backtrace?
                pass
        else:
            self._fs_regex = None
            output = True

        return output

    def match(self, cert: "EntitlementCertificate") -> bool:
        """
        Checks if the specified certificate matches this filter's restrictions.
        Returns True if the specified certificate matches this filter's restrictions ; False
        otherwise.
        """
        # Check filter string (contains-text)
        if self._fs_regex is not None:
            # Perhaps we should be validating our input object here...?
            for product in cert.products:
                if (product.name and self._fs_regex.match(product.name) is not None) or (
                    product.id and self._fs_regex.match(product.id) is not None
                ):
                    return True

        return False


class EntitlementCertificateFilter(ProductCertificateFilter):
    def __init__(self, filter_string: Optional[str] = None, service_level: Optional[str] = None):
        super(EntitlementCertificateFilter, self).__init__(filter_string=filter_string)

        self._sl_filter = None

        if service_level is not None:
            self.set_service_level(service_level)

    def set_service_level(self, service_level):
        """
        Sets this filter's required service level to the level specified. Service level filters are
        case insensitive.

        Returns True if the service level filter was set successfully; False otherwise.
        """

        output = False

        if service_level is not None:
            try:
                self._sl_filter = "" + service_level.lower()
                output = True
            except (TypeError, AttributeError):
                # Likely not a string or otherwise bad input.
                pass

        else:
            self._sl_filter = None
            output = True

        return output

    def match(self, cert):
        """
        Checks if the specified certificate matches this filter's restrictions.
        Returns True if the specified certificate matches this filter's restrictions ; False
        otherwise.
        """
        # Again: perhaps we should be validating our input object here...?

        # Check for exact match on service level:
        cert_service_level = ""  # No service level should match "".
        if cert.order and cert.order.service_level:
            cert_service_level = cert.order.service_level
        sl_check = self._sl_filter is None or cert_service_level.lower() == self._sl_filter.lower()

        # Check filter string (contains-text)
        fs_check = self._fs_regex is None or (
            super(EntitlementCertificateFilter, self).match(cert)
            or (cert.order.name and self._fs_regex.match(cert.order.name) is not None)
            or (cert.order.sku and self._fs_regex.match(cert.order.sku) is not None)
            or (cert.order.service_level and self._fs_regex.match(cert.order.service_level) is not None)
            or (cert.order.contract and self._fs_regex.match(cert.order.contract) is not None)
        )

        return sl_check and fs_check and (self._sl_filter is not None or self._fs_regex is not None)


def print_error(message: str) -> None:
    """
    Prints the specified message to stderr
    """
    sys.stderr.write(message)
    sys.stderr.write("\n")


def unique_list_items(items: Iterable, hash_function: Callable = lambda x: x) -> list:
    """
    Accepts a list of items.
    Returns a list of the unique items in the input.
    Maintains order.
    """
    observed = set()
    unique_items = []
    for item in items:
        item_key = hash_function(item)
        if item_key in observed:
            continue
        else:
            unique_items.append(item)
            observed.add(item_key)
    return unique_items


def generate_correlation_id() -> str:
    return str(uuid.uuid4()).replace("-", "")  # FIXME cp should accept -


def get_process_names() -> Iterator[str]:
    """
    Returns a list of "Name" values for all processes running on the system.
    This assumes an accessible and standard procfs at "/proc/".
    It will only work on unix-like systems.
    """
    proc_name_expr = r"[Nn][Aa][Mm][Ee]:?[\s]*(?P<proc_name>.*)"
    for subdir in os.listdir("/proc"):
        if re.match("[0-9]+", subdir):
            process_status_file_path = os.path.join(os.path.sep, "proc", subdir, "status")
            status_file = None
            lines = ""
            try:
                status_file = open(process_status_file_path)
                lines = "".join(status_file.readlines())
            except IOError as e:
                # See https://bugzilla.redhat.com/show_bug.cgi?id=1890080
                # Sometimes when processes are killed after we have listed the
                # /proc dir content we can end up trying to open a file which no
                # longer exists.
                log.debug(
                    "A process has likely ended before it's status could be read for"
                    " {subdir} : {ex}".format(subdir=subdir, ex=e)
                )
                continue
            except Exception as e:
                log.debug(
                    "Unexpected exception while trying to read process names from /proc for"
                    " {subdir} : {ex}".format(subdir=subdir, ex=e)
                )
                continue
            finally:
                if status_file is not None:
                    status_file.close()

            # Find first value of something that looks like "Name: THING"
            match = re.search(proc_name_expr, lines)
            if match:
                proc_name = match.groupdict().get("proc_name")
                proc_id = int(subdir)
                if proc_name:
                    yield proc_name, proc_id


def is_process_running(process_to_find: str, process_id_to_find: int = None) -> bool:
    """
    Check if process with given name is running
    :param process_to_find: string with process name
    :param process_id_to_find: int with process ID
    :return: True, when at least one process is running; Otherwise returns False
    """
    for process_name, process_id in get_process_names():
        if process_to_find == process_name:
            if process_id_to_find is None:
                return True
            else:
                if process_id_to_find == process_id:
                    return True
    return False


def is_interactive() -> bool:
    """
    Check if the process is running in an interactive session.
    :return: True, when the process is running in an interactive session; Otherwise returns False
    """
    return sys.stdin and sys.stdin.isatty()


def terminal_printable_content(content: str) -> str:
    """
    Get the content of the reply in a way suitable to print on terminal;
    in particular, this means that any non-printable character
    (excluding new lines and tabs) is replaced with "<$code>".
    """
    buf = io.StringIO()
    for c in content:
        if c.isprintable() or c == "\n" or c == "\t":
            buf.write(c)
        else:
            buf.write(f"<{ord(c)}>")
    return buf.getvalue()
