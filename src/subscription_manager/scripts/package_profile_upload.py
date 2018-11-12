from __future__ import print_function, division, absolute_import

# Copyright (c) 2018 Red Hat, Inc.
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
import six
import sys

if six.PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

import argparse

from subscription_manager.injectioninit import init_dep_injection
init_dep_injection()

from subscription_manager.i18n import configure_i18n, ugettext as _
configure_i18n()

from subscription_manager import logutil
logutil.init_logger()

from subscription_manager import packageprofilelib


def main():
    parser = argparse.ArgumentParser(description=_("Upload a package profile"))
    parser.add_argument("--force-upload", action="store_true", help=_("Force package profile upload"))
    args = parser.parse_args()

    command = packageprofilelib.PackageProfileActionCommand()
    report = command.perform(force_upload=args.force_upload)

    if report._status == 0:
        print(_("No updates performed. See /var/log/rhsm/rhsm.log for more information."))
    else:
        print(report)


if __name__ == '__main__':
    try:
        sys.exit(abs(main() or 0))
    except SystemExit as sys_err:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except IOError:
            pass
        raise sys_err
    except KeyboardInterrupt:
        sys.stderr.write("\n" + _("User interrupted process."))
        sys.exit(0)
    except Exception as err:
        sys.stderr.write(_("Error uploading package profile: %s\n") % err)
        sys.exit(-1)
