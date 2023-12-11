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
import enum
import functools
import os
import re
import sys
import time
import threading
from typing import Callable, List, Optional, TextIO, Tuple, Union, Generator

import urllib.parse

import rhsm.config
from rhsm.config import DEFAULT_PROXY_PORT


PROGRESS_MESSAGES: bool = True
"""Enable or disable progress messages.

Please note that they can be also disabled via rhsm.conf file or with
environment variable (when debugging is turned on), this variable (working as
module singleton) is used for turning it off dynamically via CLI option.
"""


class COLOR(enum.Enum):
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def colorize(text: str, color: COLOR) -> str:
    return color.value + text + COLOR.RESET.value


def remove_scheme(uri: str) -> str:
    """Remove the scheme component from a URI."""
    return re.sub("^[A-Za-z][A-Za-z0-9+-.]*://", "", uri)


class ServerUrlParseError(Exception):
    def __init__(self, serverurl: str, msg: str = None):
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


def has_bad_scheme(url: str) -> bool:
    """Check a url for an invalid or unuseful schema.

    Don't allow urls to start with :/ http/ https/ non http/httpsm or http(s) with single /

    :params url: URL string to check
    :returns: True if the url scheme is "bad"
    """
    match_bad = r"(https?[:/])|(:/)|(\S+://)"
    match_good = r"https?://"
    # Testing good first allows us to exclude some regex for bad
    if re.match(match_good, url):
        return False
    if re.match(match_bad, url):
        return True
    return False


def has_good_scheme(url: str) -> bool:
    match = re.match(r"https?://(\S+)?", url)
    if not match:
        return False
    # a good scheme alone is not really a good scheme
    if not match.group(1):
        raise ServerUrlParseErrorJustScheme(url)
    return True


def parse_url(
    local_server_entry: str,
    default_hostname: str = None,
    default_port: str = None,
    default_prefix: str = None,
    default_username: str = None,
    default_password: str = None,
) -> Tuple[str, str, str, str, str]:
    """
    Parse hostname, port, and webapp prefix from the string a user entered.
    Expected format: username:password@hostname:port/prefix
    :param local_server_entry: URL of a candlepin server
    :param default_hostname: default hostname
    :param default_port: default port
    :param default_prefix: default prefix (e.g. /candlepin)
    :param default_username: not encrypted default username
    :param default_password: not encrypted dfault password
    :return: a tuple of (username, password, hostname, port, path)
    """

    if local_server_entry == "":
        raise ServerUrlParseErrorEmpty(local_server_entry, "Server entry is empty")

    if local_server_entry is None:
        raise ServerUrlParseErrorNone(local_server_entry, "No server entry provided")

    # good_url in this case meaning a schema we support, and
    # _something_ else. This is to make urlparse happy
    good_url: Union[str, None] = None

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

    # No need to do error-checking here since urlparse
    # always returns a 6-length named tuple -- only consideration
    # to note is that the urlparse input is a valid string.
    result = urllib.parse.urlparse(good_url)

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


def get_env_proxy_info() -> dict:
    the_proxy = {
        "proxy_username": "",
        "proxy_hostname": "",
        "proxy_port": "",
        "proxy_password": "",
    }

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
        the_proxy["proxy_username"] = info[0]
        the_proxy["proxy_password"] = info[1]
        the_proxy["proxy_hostname"] = info[2]
        if info[3] is None or info[3] == "":
            the_proxy["proxy_port"] = None
        else:
            the_proxy["proxy_port"] = int(info[3])
    return the_proxy


def cmd_name(argv: List[str]) -> str:
    """Attempt to get a meaningful command name from argv.

    This handles cases where argv[0] isn't helpful (for
    example, '/usr/bin/python' or '__main__.py'.
    """
    cmd_name_string = os.path.basename(argv[0])
    return cmd_name_string


def fix_no_proxy() -> None:
    """
    This fixes no_proxy/NO_PROXY environment to not include leading
    asterisk, because there is some imperfection in proxy_bypass_environment.
    """

    # This fixes BZ: 1443164, because proxy_bypass_environment() from urllib does
    # not support no_proxy with items containing asterisk (e.g.: *.redhat.com)

    no_proxy = os.environ.get("no_proxy") or os.environ.get("NO_PROXY")
    if no_proxy is not None:
        if no_proxy != "*":
            # Remove all leading white spaces and asterisks from items of no_proxy
            # except item containing only "*" (urllib supports alone asterisk).
            no_proxy = ",".join([item.lstrip(" *") for item in no_proxy.split(",")])
            # Save no_proxy back to 'no_proxy' and 'NO_PROXY'
            os.environ["no_proxy"] = no_proxy
            os.environ["NO_PROXY"] = no_proxy


def suppress_output(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        devnull: Optional[TextIO] = None
        stdout: Optional[TextIO] = None
        stderr: Optional[TextIO] = None
        try:
            devnull = open(os.devnull, "w")
            stdout = sys.stdout
            stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            return func(*args, **kwargs)
        finally:
            if stdout is not None:
                sys.stdout = stdout
            if stderr is not None:
                sys.stderr = stderr
            if devnull is not None:
                devnull.close()

    return wrapper


def singleton(cls: type) -> type:
    """Decorate a class to make it singleton.

    This decorator is inherited: subclasses will be singletons as well,
    but they won't be the same singleton as their parent.
    """

    __orig_new__: Callable = cls.__new__
    cls._instance = None

    def __new__(kls, *args, **kwargs):
        if not isinstance(kls._instance, kls):
            if __orig_new__ is object.__new__:
                # Default __new__ only takes the class as an argument
                kls._instance = __orig_new__(kls)
            else:
                kls._instance = __orig_new__(kls, *args, **kwargs)
        return kls._instance

    cls.__new__ = __new__
    return cls


def call_once(fn: Callable) -> Callable:
    """Decorate a function to make it callable just once.

    All further calls do not do anything and return None.
    """
    fn._call_once_lock = threading.RLock()
    fn._called = False

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        locked: bool = fn._call_once_lock.acquire(blocking=True, timeout=1.0)
        if not locked:
            raise RuntimeError(f"Could not acquire call_once lock for function {fn.__name__}.")

        try:
            if fn._called:
                return None
            # We want to allow running the function once even if it raises exception.
            fn._called = True
            fn_result = fn(*args, **kwargs)
            return fn_result
        finally:
            fn._call_once_lock.release()

    def _reset():
        """Reset function state to allow another call to it.

        This is used for testing purposes, there is no need to call this in
        production code itself.
        """
        locked: bool = fn._call_once_lock.acquire(blocking=True, timeout=1.0)
        if not locked:
            raise RuntimeError(f"Could not acquire call_once lock for function {fn.__name__}.")

        try:
            fn._called = False
        finally:
            fn._call_once_lock.release()

    wrapper._reset = _reset

    return wrapper


def lock(cls: type) -> type:
    """Decorate a class to make it thread-safe lock.

    It will provide read-only 'locked' attribute, functions lock() and unlock()
    and __enter__/__exit__ methods for context manager functionality.
    """

    cls._lock = threading.RLock()
    """Actual lock providing locking functionality."""
    cls._locked = False
    """Even though _lock._is_owned() would work better,
    it is not part of public API, and it should not be used in production.
    """

    cls.locked = property(fget=lambda self: self._locked)

    def lock(self) -> None:
        """Lock using RLock.

        One thread can acquire the lock multiple times, but other threads cannot
        until the lock is completely unlocked.
        """
        self._lock.acquire()
        self._locked = True

    def unlock(self) -> None:
        """Unlock the lock."""
        try:
            self._lock.release()
        except RuntimeError:
            # This exception is raised when the lock was not acquired
            pass
        finally:
            self._locked = False

    def __enter__(self) -> cls:
        self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.unlock()

    cls.lock = lock
    cls.unlock = unlock
    cls.__enter__ = __enter__
    cls.__exit__ = __exit__

    return cls


class StatusMessage:
    """Class for temporary reporting.

    While you can call 'print()' and 'clean()' methods directly, the easier
    way is to use context manager: 'with StatusMessage("Fetching data"):'.

    This object will print the description to stdout when called. When the
    context manager exists (either because the code finished or because an
    error got raised inside), printed output will be cleared before the
    program continues with its execution. This ensures that the message will
    disappear after it's no longer valid.
    """

    def __init__(self, description: Optional[str]):
        if description is None:
            description = "Transmitting data"
        self.raw_text = description

        CURSIVE = "\033[3m"
        RESET = "\033[0m"

        self.text = f"{CURSIVE}{self.raw_text}{RESET}"

        self.quiet = False
        config = rhsm.config.get_config_parser()
        if config.get("rhsm", "progress_messages") == "0":
            self.quiet = True
        if not PROGRESS_MESSAGES:
            self.quiet = True
        if not sys.stdout.isatty():
            self.quiet = True
        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST", ""):
            self.quiet = True

    def print(self) -> None:
        if self.quiet:
            return
        print(self.text, end="\r")

    def clean(self) -> None:
        if self.quiet:
            return
        print("\033[0K", end="\r")

    def __enter__(self) -> None:
        self.print()

    def __exit__(self, error_type, error_value, traceback) -> None:
        self.clean()
        if error_type:
            raise


class StatusSpinnerStyle:
    """Class for spinner animations.

    While subscription-manager may not be using all spinners used below,
    they have been defined here, so they can be easily used in the future.

    The default spinner, LINE, has been chosen for several reasons:
    - it is small (only one character wide),
    - it has small loop cycle (so quickly switching several status messages
      looks like it is one spinner with several messages, even though every
      message has its own spinner),
    - it is only made of ASCII characters (which makes it renderable on
      all TTYs, not just rich terminal emulators in GUI).
    """

    LINE: Tuple[str] = ("|", "/", "-", "\\")
    BRAILLE: Tuple[str] = ("⠋", "⠙", "⠸", "⠴", "⠦", "⠇")
    WIDE_BRAILLE: Tuple[str] = ("⠧ ", "⠏ ", "⠋⠁", "⠉⠉", "⠈⠙", " ⠹", " ⠼", "⠠⠴", "⠤⠤", "⠦⠄")
    BAR_FORWARD: Tuple[str] = ("[    ]", "[=   ]", "[==  ]", "[=== ]", "[====]", "[ ===]", "[  ==]", "[   =]")
    BAR_BACKWARD: Tuple[str] = (
        "[    ]",
        "[   =]",
        "[  ==]",
        "[ ===]",
        "[====]",
        "[=== ]",
        "[==  ]",
        "[=   ]",
    )
    BAR_BOUNCE: Tuple[str] = BAR_FORWARD + BAR_BACKWARD


class LiveStatusMessage(StatusMessage):
    """Class for temporary reporting, with activity spinner.

    While you can call 'print()' and 'clean()' methods directly, the easier
    way is to use context manager: 'with LiveStatusMessage("Fetching data"):'.

    This object will print the description to stdout when called. When the
    context manager exists (either because the code finished or because an
    error got raised inside), printed output will be cleared before the
    program continues with its execution. This ensures that the message will
    disappear after it's no longer valid.

    You can set several loading styles (via class StatusSpinnerStyle) or choose
    the speed in which the animation is played (per frame, in seconds).
    """

    def __init__(
        self,
        description: Optional[str],
        *,
        style: List[str] = StatusSpinnerStyle.LINE,
        placement: str = "BEFORE",
        speed: float = 0.15,
    ) -> None:
        super().__init__(description)

        # Do not use cursive if there is a spinner. When the message is
        # displayed without the spinner (using plain StatusMessage class)
        # the cursive is used to visually separate the status message from
        # real output. When we have a spinner, it is not necessary, because
        # the spinner itself is making that visual difference.
        self.text = self.raw_text

        self.busy: bool = False
        self._loops: int = 0
        self._thread: Union[threading.Thread, None] = None
        self._cursor: bool = True

        self.frames: List[str] = style
        self.delay: float = speed
        if placement not in ("BEFORE", "AFTER"):
            raise ValueError(f"String {placement} is not valid spinner placement.")
        self.placement: str = placement

    @property
    def spinner_frame(self) -> Generator[str, None, None]:
        """Get next frame of the spinner animation."""
        while True:
            yield self.frames[self._loops % len(self.frames)]

    @property
    def cursor(self) -> bool:
        """Get cursor visibility state."""
        return self._cursor

    @cursor.setter
    def cursor(self, enable: bool) -> None:
        """Enable or disable cursor.

        For more information on these rarely used shell escape codes, see
        https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_(Control_Sequence_Introducer)_sequences
        """
        if type(enable) is not bool:
            raise ValueError(f"Expected bool, got {type(enable)!s}")
        if enable:
            print("\033[?25h", end="")
            self._cursor = True
        else:
            print("\033[?25l", end="")
            self._cursor = False

    def __enter__(self) -> None:
        self.busy = True
        if self.quiet:
            return
        self.cursor = False
        self._thread = threading.Thread(target=self.loop)
        self._thread.start()

    def __exit__(self, error_type, error_value, traceback) -> None:
        self.busy = False
        if self.quiet:
            if error_type:
                raise
            return
        self.cursor = True
        self._thread.join(timeout=self.delay)
        if error_type:
            raise

    def print(self) -> None:
        if self.quiet:
            return
        frame: str = next(self.spinner_frame)
        line: str
        if self.placement == "BEFORE":
            line = frame + " " + self.text
        else:
            line = self.text + " " + frame
        print(line, end="\r")

    def clean(self) -> None:
        if self.quiet:
            return
        print("\033[0K", end="\r")

    def loop(self) -> None:
        """Show pretty animation while we fetch data."""
        while self.busy:
            self.print()
            self._loops += 1
            time.sleep(self.delay)
            self.clean()
