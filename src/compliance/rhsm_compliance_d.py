#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: James Bowes <jbowes@redhat.com>
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

import syslog
import glib
import gobject
import dbus
import dbus.service

from dbus.mainloop.glib import DBusGMainLoop
from optparse import OptionParser

import sys
sys.path.append("/usr/share/rhsm")
import managerlib

enable_debug = False

def debug(msg):
    if enable_debug:
        print msg


def check_compliance():
    products = managerlib.getInstalledProductStatus()

    # XXX we'll have to watch this with i18n

    not_compliant = [x for x in products \
            if x[1] not in ["Subscribed", "Not Installed"]]

    if len(not_compliant) > 0:
        debug("System is not in compliance")
        debug(not_compliant)
    else:
        debug("System appears compliant")
    return len(not_compliant) == 0


def check_if_ran_once(compliance, loop):
    if compliance.has_run:
        debug("dbus has been called once, quitting")
        loop.quit()
    return True


class ComplianceChecker(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)
        self.has_run = False

    @dbus.service.method(
        dbus_interface="com.redhat.SubscriptionManager.Compliance",
        out_signature='b')
    def check_compliance(self):
        ret = check_compliance()
        self.has_run = True
        return ret


def main():
    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug",
            help="Display debug messages", action="store_true", default=False)
    parser.add_option("-k", "--keep-alive", dest="keep_alive",
            help="Stay running (don't shut down after the first dbus call)",
            action="store_true", default=False)
    parser.add_option("-s", "--syslog", dest="syslog",
            help="Run standalone and log result to syslog",
            action="store_true", default=False)

    options, args = parser.parse_args()
    
    global enable_debug
    enable_debug = options.debug

    # short-circuit dbus initialization
    if options.syslog:
        compliant = check_compliance()
        if not compliant:
            syslog.openlog("rhsm-complianced")
            syslog.syslog(syslog.LOG_NOTICE,
                    "This system is non-compliant. " +
                    "Please run subscription-manager-cli for more information.")
        return


    DBusGMainLoop(set_as_default=True)

    system_bus = dbus.SystemBus()
    name = dbus.service.BusName("com.redhat.SubscriptionManager", system_bus)
    compliance = ComplianceChecker(system_bus, "/Compliance")

    loop = gobject.MainLoop()

    if not options.keep_alive:
        glib.idle_add(check_if_ran_once, compliance, loop)

    loop.run()


if __name__ == "__main__":
    main()
