from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2016 Red Hat, Inc.
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
import logging

# Init logging very early so we can log any issues that occur at import time
logging.basicConfig(level=logging.DEBUG, format="%(levelname)5s [%(name)s:%(lineno)s] %(message)s")
log = logging.getLogger('')
log.setLevel(logging.INFO)

import sys
from rhsmlib.dbus import service_wrapper
from rhsmlib.dbus.facts import base, constants


def main():
    try:
        object_classes = [
            base.AllFacts,
        ]
        sys.exit(service_wrapper.main(
            sys.argv,
            object_classes=object_classes,
            default_bus_name=constants.FACTS_DBUS_NAME)
        )
    except Exception:
        log.exception("DBus service startup failed")

if __name__ == "__main__":
    main()
