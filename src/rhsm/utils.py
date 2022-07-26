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

import functools
import os
import sys
import time
import threading
from typing import Callable, List, Optional

import rhsm.config

PROGRESS_MESSAGES: bool = True
"""Enable or disable progress messages.

Please note that they can be also disabled via rhsm.conf file or with
environment variable (when debugging is turned on), this variable (working as
module singleton) is used for turning it off dynamically via CLI option.
"""


def cmd_name(argv):
    """Attempt to get a meaningful command name from argv.

    This handles cases where argv[0] isn't helpful (for
    example, '/usr/bin/python' or '__main__.py'.
    """
    cmd_name_string = os.path.basename(argv[0])
    return cmd_name_string


def fix_no_proxy():
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


def suppress_output(func):
    def wrapper(*args, **kwargs):
        try:
            devnull = open(os.devnull, "w")
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


def parse_bool(string: str) -> bool:
    """Parse a string into True or False.

    Recognized boolean pairs are 1/0, true/false, yes/no, on/off, case insensitive.

    :raises: ValueError if the string is not recognized.
    """
    string = string.lower()
    if string in ("1", "true", "yes", "on"):
        return True
    if string in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"Value {string} is not recognized boolean value.")


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
        if parse_bool(os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST", "0")):
            self.quiet = True

    def print(self):
        if self.quiet:
            return
        print(self.text, end="\r")

    def clean(self):
        if self.quiet:
            return
        print(" " * len(self.text), end="\r")

    def __enter__(self):
        self.print()

    def __exit__(self, error_type, error_value, traceback):
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

    LINE: List[str] = ["|", "/", "-", "\\"]
    BRAILLE: List[str] = ["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"]
    WIDE_BRAILLE: List[str] = ["⠧ ", "⠏ ", "⠋⠁", "⠉⠉", "⠈⠙", " ⠹", " ⠼", "⠠⠴", "⠤⠤", "⠦⠄"]
    BAR_FORWARD: List[str] = ["[    ]", "[=   ]", "[==  ]", "[=== ]", "[====]", "[ ===]", "[  ==]", "[   =]"]
    BAR_BACKWARD: List[str] = ["[    ]", "[   =]", "[  ==]", "[ ===]", "[====]", "[=== ]", "[==  ]", "[=   ]"]
    BAR_BOUNCE: List[str] = BAR_FORWARD + BAR_BACKWARD


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
    ):
        super().__init__(description)

        # Do not use cursive if there is a spinner. When the message is
        # displayed without the spinner (using plain StatusMessage class)
        # the cursive is used to visually separate the status message from
        # real output. When we have a spinner, it is not necessary, because
        # the spinner itself is making that visual difference.
        self.text = self.raw_text

        self.busy: bool = False
        self._loops: int = 0
        self._thread: threading.Thread = None
        self._cursor: bool = True

        self.frames: str = style
        self.delay: float = speed
        if placement not in ("BEFORE", "AFTER"):
            raise ValueError(f"String {placement} is not valid spinner placement.")
        self.placement: str = placement

    @property
    def spinner_frame(self):
        """Get next frame of the spinner annimation."""
        while True:
            yield self.frames[self._loops % len(self.frames)]

    @property
    def max_text_width(self) -> int:
        """Get the length of the longest line possible.

        This is used so we can properly clean the console when we exit.
        """
        max_frame_length: int = len(max(self.frames, key=len))
        return len(self.text) + max_frame_length + 1

    @property
    def cursor(self) -> bool:
        """Get cursor visibility state."""
        return self._cursor

    @cursor.setter
    def cursor(self, enable: bool):
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

    def __enter__(self):
        self.busy = True
        if self.quiet:
            return
        self.cursor = False
        self._thread = threading.Thread(target=self.loop)
        self._thread.start()

    def __exit__(self, error_type, error_value, traceback):
        self.busy = False
        if self.quiet:
            if error_type:
                raise
            return
        self.cursor = True
        self._thread.join(timeout=self.delay)
        if error_type:
            raise

    def print(self):
        if self.quiet:
            return
        frame: str = next(self.spinner_frame)
        line: str
        if self.placement == "BEFORE":
            line = frame + " " + self.text
        else:
            line = self.text + " " + frame
        print(line, end="\r")

    def clean(self):
        if self.quiet:
            return
        print(" " * self.max_text_width, end="\r")

    def loop(self):
        """Show pretty animation while we fetch data."""
        while self.busy:
            self.print()
            self._loops += 1
            time.sleep(self.delay)
            self.clean()
