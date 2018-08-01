# -*- coding: utf-8 -*-

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

# hack to allow bytes/strings to be interpolated w/ unicode values (gettext gives us bytes)
# Without this, for example, "Формат: %s\n" % u"foobar" will fail with UnicodeDecodeError
# See http://stackoverflow.com/a/29832646/6124862 for more details
import six
import sys
if six.PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

from rhsmlib.dbus import service_wrapper
from rhsmlib.dbus import objects


def main():
    try:
        object_classes = [
            objects.ConfigDBusObject,
            objects.RegisterDBusObject,
            objects.AttachDBusObject,
            objects.ProductsDBusObject,
            objects.UnregisterDBusObject,
            objects.EntitlementDBusObject,
            objects.ConsumerDBusObject,
            objects.SyspurposeDBusObject,
            objects.Main
        ]
        sys.exit(service_wrapper.main(sys.argv, object_classes=object_classes))
    except Exception:
        log.exception("DBus service startup failed")

if __name__ == '__main__':
    main()
