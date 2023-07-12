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
import argparse
import os
import sys
from typing import List, Optional, TYPE_CHECKING, Type

import dbus
import dbus.mainloop.glib
import rhsmlib
import logging

import rhsmlib.dbus.constants
from rhsmlib.dbus import server
from subscription_manager.i18n import ugettext as _
from subscription_manager.cli import system_exit

if TYPE_CHECKING:
    import dbus.service
    from rhsmlib.dbus.base_object import BaseObject

log = logging.getLogger(__name__)


def parse_argv(argv, default_dbus_name):
    parser = argparse.ArgumentParser(usage="usage: %(prog)s [options] [class name]")
    parser.add_argument(
        "-b",
        "--bus",
        action="store",
        dest="bus",
        help="Bus to use (defaults to dbus.SystemBus)",
    )
    parser.add_argument("-n", "--bus-name", default=default_dbus_name)
    parser.add_argument("-v", "--verbose", action="store_true")
    (opts, args) = parser.parse_known_args(argv[1:])

    try:
        if hasattr(opts, "bus") and opts.bus:
            opts.bus = rhsmlib.import_class(opts.bus)
        else:
            opts.bus = dbus.SystemBus
    except (AttributeError, ValueError):
        system_exit(os.EX_USAGE, _("Error: Unable to load bus '{name}'").format(name=opts.bus))

    return opts, args


def main(
    argv=sys.argv,
    object_classes: List[Type["BaseObject"]] = None,
    default_bus_name: Optional[str] = None,
) -> int:
    # Set default mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    if not default_bus_name:
        default_bus_name = rhsmlib.dbus.constants.BUS_NAME

    options, args = parse_argv(argv, default_bus_name)

    if options.verbose:
        logger = logging.getLogger("")
        logger.setLevel(logging.DEBUG)

    if not object_classes:
        # Read the object classes from the command-line if we don't
        # get anything as a parameter
        object_classes = []
        for clazz in args:
            object_classes.append(rhsmlib.import_class(clazz))

    try:
        log.debug("Starting DBus service with name %s" % options.bus_name)
        server.Server(bus_class=options.bus, bus_name=options.bus_name, object_classes=object_classes).run()
    except dbus.exceptions.DBusException as e:
        if e._dbus_error_name == "org.freedesktop.DBus.Error.AccessDenied":
            print(
                "Access to DBus denied.  You need to edit /etc/dbus-1/system.conf to allow %s or run with "
                "dbus-daemon and a custom config file." % options.bus_name
            )
    return 0
