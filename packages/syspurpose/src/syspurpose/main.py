# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
#
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

import sys
from syspurpose import cli
from syspurpose.utils import system_exit

import syspurpose.i18n as i18n
i18n.configure_i18n()

from syspurpose.i18n import ugettext as _


def main():
    try:
        sys.exit(cli.main() or 0)
    except KeyboardInterrupt:
        system_exit(0, _("User interrupted process"))
    except Exception as e:
        system_exit(-1, str(e))


if __name__ == "__main__":
    main()
