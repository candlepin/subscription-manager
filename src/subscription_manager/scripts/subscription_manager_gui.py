# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

#
# wrapper for subscription Manager commandline tool.
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi
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

import warnings
# this is a deprecation warning we see on rhel6, but the
# functionality doesn't seem to exist in public api yet
# Note that you do not see this on python2.7 systems as
# deprecationWarnings are ignored by default
warnings.filterwarnings(action="ignore",
                        category=DeprecationWarning,
                        message="^The dbus_bindings module is not public API and will go away soon.")

import os
import dbus
import dbus.service
import dbus.glib
import dbus.exceptions
import logging
import signal

from subscription_manager.i18n import ugettext as _

signal.signal(signal.SIGINT, signal.SIG_DFL)

# Capture python (and pygtk) warnings that normally print to
# stderr and log them.
# Additional warnings filters are in gui/widgets.py
log = logging.getLogger("rhsm-app.subscription-manager-gui")

try:
    # python 2.7+ only
    logging.captureWarnings(True)
except AttributeError:
    pass


# Since the location of these def's keeps moving, hardcoded them here as per the spec
# see http://dbus.freedesktop.org/doc/dbus-specification.html#message-bus-names
REQUEST_NAME_REPLY_PRIMARY_OWNER = 1
REQUEST_NAME_REPLY_ALREADY_OWNER = 4

# To figure out if we got the bus name we wanted, and if not,
# why not, we need the results from request_name, and to
# see if it's return codes are REQUEST_NAME_REPLY_PRIMARY_OWNER
# or REQUEST_NAME_REPLY_ALREADY_OWNER.
#
# We have to support dbus-python ~ 0.7, from ~2005 for rhel5
# which require the use of "dbus.dbus_bindings".
# 'dbus_bindings' has been deprecated since ~2006  (~0.8.x)
# and were finally removed from the dbus-python bindings
# in rhel7. So for rhel5, we conditionally import dbus_bindings
# use bus_request_name, otherwise we use the newer bus.request_name


def _request_name_rhel5(bus, bus_name):
    return dbus.dbus_bindings.bus_request_name(bus.get_connection(), bus_name.get_name())


def _request_name(bus, bus_name):
    return bus.request_name(bus_name.get_name())


try:
    import dbus.dbus_bindings
    request_name = _request_name_rhel5
except ImportError as e:
    request_name = _request_name


def system_exit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(str(msg) + '\n')
    sys.exit(code)


BUS_NAME = "com.redhat.SubscriptionManagerGUI"
BUS_PATH = "/gui"

_LIBPATH = "/usr/share/rhsm"
# add to the path if need be
if _LIBPATH not in sys.path:
    sys.path.append(_LIBPATH)

# quick check to see if you are a super-user.
if os.getuid() != 0:
    sys.stderr.write('Error: must be root to execute\n')
    sys.exit(8)

try:
    from subscription_manager import ga_loader
    ga_loader.init_ga()
    from subscription_manager.ga import Gtk as ga_Gtk
    from subscription_manager.ga import gtk_compat
    gtk_compat.threads_init()
except RuntimeError as e:
    system_exit(2, "Unable to start.  Error: %s" % e)

try:
    # this has to be done first thing due to module level translated vars.
    from subscription_manager.i18n import configure_i18n
    configure_i18n()

    from rhsm import logutil

    logutil.init_logger()

    from subscription_manager.injectioninit import init_dep_injection
    init_dep_injection()

    import subscription_manager.injection as inj
    # Set up DBus mainloop via DBUS_IFACE
    inj.require(inj.DBUS_IFACE)

    from subscription_manager.gui import managergui
    from subscription_manager.i18n_argparse import ArgumentParser, USAGE
except ImportError as e:
    log.exception(e)
    system_exit(2, "Unable to find Subscription Manager module.\n"
                  "Error: %s" % e)


class SubscriptionManagerService(dbus.service.Object):
    def __init__(self, window):
        self.window = window
        bus_name = dbus.service.BusName(BUS_NAME, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, BUS_PATH)

    @dbus.service.method(dbus_interface=BUS_NAME)
    def show_window(self):
        self.window.present()


def already_running(bus):
    if bus is None:
        return False

    bus_name = dbus.service.BusName(BUS_NAME, bus=dbus.SessionBus())
    request_name_res = request_name(bus, bus_name)

    if bus and ((request_name_res != REQUEST_NAME_REPLY_PRIMARY_OWNER) and
       (request_name_res != REQUEST_NAME_REPLY_ALREADY_OWNER)):
        print(_("%s is already running") % "subscription-manager-gui")
        return True
    return False


def main():
    parser = ArgumentParser(usage=USAGE)
    parser.add_option("--register", action='store_true',
                      help=_("launches the registration dialog on startup"))
    options, args = parser.parse_known_args(args=sys.argv)

    log = logging.getLogger("rhsm-app.subscription-manager-gui")

    try:
        bus = dbus.SessionBus()
    except dbus.exceptions.DBusException as e:
        log.debug("Enabled to connect to dbus SessionBus")
        log.exception(e)
        # Just ignore it if for some reason we can't find the session bus
        bus = None

    if already_running(bus):
        # Attempt to raise the running instance to the forefront
        try:
            remote_object = bus.get_object(BUS_NAME, BUS_PATH)
            remote_object.show_window(dbus_interface=BUS_NAME)
            log.debug("subscription-manager-gui already running, showing main window")
        except dbus.exceptions.DBusException as e:
            log.debug("Error attempting to show main window via dbus")
            log.debug("dbus remote_object with no show_window: %s" % remote_object)
            log.debug(e)
            # failed to raise the window, maybe we raced dbus?
            # fallback to opening a new window
        else:
            # we raised the existing window, we are done
            sys.exit()

    try:
        main = managergui.MainWindow(auto_launch_registration=options.register)

        # Hook into dbus service - only if it is available
        if bus:
            SubscriptionManagerService(main.main_window)

        # Exit the gtk loop when the window is closed
        main.main_window.connect('hide', ga_Gtk.main_quit)

        sys.exit(ga_Gtk.main() or 0)
    except SystemExit as e:
        # this is a non-exceptional exception thrown by Python 2.4, just
        # re-raise, bypassing handle_exception
        raise e
    except KeyboardInterrupt:
        system_exit(0, "\nUser interrupted process.")
    except Exception as e:
        log.exception(e)
        system_exit(1, e)


if __name__ == '__main__':
    main()
