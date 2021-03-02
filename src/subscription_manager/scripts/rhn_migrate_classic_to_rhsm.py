# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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

# hack to allow bytes/strings to be interpolated w/ unicode values (gettext gives us bytes)
# Without this, for example, "Формат: %s\n" % u"foobar" will fail with UnicodeDecodeError
# See http://stackoverflow.com/a/29832646/6124862 for more details
import six
import sys
if six.PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
import os


def system_exit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(six.text_type(msg) + '\n')
    sys.exit(code)

_LIBPATH = "/usr/share/rhsm"
# add to the path if need be
if _LIBPATH not in sys.path:
    sys.path.append(_LIBPATH)

# quick check to see if you are a super-user.
if os.getuid() != 0:
    sys.stderr.write('Error: this command requires root access to execute\n')
    sys.exit(8)

try:
    # this has to be done first thing due to module level translated vars.
    from subscription_manager.i18n import configure_i18n
    configure_i18n()

    from rhsm import logutil

    logutil.init_logger()

    from subscription_manager.injectioninit import init_dep_injection
    init_dep_injection()

    from subscription_manager.migrate import migrate
    from subscription_manager.cli_command.cli import handle_exception
except KeyboardInterrupt:
    system_exit(0, "\nUser interrupted process.")
except ImportError as err:
    system_exit(2, "Unable to find Subscription Manager module.\n"
                   "Error: %s" % err)


def main():
    # execute
    try:
        return migrate.main()
    except KeyboardInterrupt:
        system_exit(0, "\nUser interrupted process.")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(abs(main() or 0))
    except SystemExit as sys_err:
        # this is a non-exceptional exception thrown by Python 2.4, just
        # re-raise, bypassing handle_exception
        raise sys_err
    except KeyboardInterrupt:
        system_exit(0, "\nUser interrupted process.")
    except Exception as err:
        handle_exception("Exception caught in rhm-migrate-classic-to-rhsm", err)
