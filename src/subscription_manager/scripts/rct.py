# Copyright (c) 2010 - 2012 Red Hat, Inc.
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
# Without this, for example, "Формат: %s\n" % "foobar" will fail with UnicodeDecodeError
# See http://stackoverflow.com/a/29832646/6124862 for more details
import sys

from subscription_manager.i18n import configure_i18n, ugettext as _
from rhsm import logutil
from rct.cli import RctCLI

configure_i18n()
logutil.init_logger()


def main():
    return RctCLI().main()


if __name__ == "__main__":
    try:
        sys.exit(abs(main() or 0))
    except SystemExit as err:
        # This is a non-exceptional exception thrown by Python 2.4, just
        # re-raise, bypassing handle_exception
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except IOError:
            pass
        raise err
    except KeyboardInterrupt:
        sys.stderr.write("\n" + _("User interrupted process."))
        sys.exit(0)
