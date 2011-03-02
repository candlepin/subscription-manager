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

import datetime
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
import rhsm.certificate as certificate
import certlib

enable_debug = False

RHSM_EXPIRED   = 0
RHSM_COMPLIANT = 1
RHSM_WARNING   = 2
RHN_CLASSIC    = 3


def debug(msg):
    if enable_debug:
        print msg


def in_warning_period(sorter):

    for entitlement in sorter.expired_entitlement_certs:
        warning_period = datetime.timedelta(
                days=int(entitlement.getOrder().getWarningPeriod()))
        valid_range = entitlement.validRange()
        warning_range = certificate.DateRange(
                valid_range.end() - warning_period, valid_range.end())
        if warning_range.hasNow():
            return True

    return False


def check_compliance():

    if managerlib.is_registered_with_classic():
        debug("System is already registered with RHN Classic")
        return RHN_CLASSIC

    sorter = certlib.CertSorter(certlib.ProductDirectory(),
            certlib.EntitlementDirectory())

    if len(sorter.unentitled_products.keys()) > 0 or len(sorter.expired_products.keys()) > 0:
        debug("System is not in compliance")
        debug(sorter.unentitled_products.keys())
        debug(sorter.expired_products.keys())
        return RHSM_EXPIRED
    else:
        if in_warning_period(sorter):
            debug("System has one or more entitlements in their warning period")
            return RHSM_WARNING
        else:
            debug("System appears compliant")
            return RHSM_COMPLIANT


def check_if_ran_once(compliance, loop):
    if compliance.has_run:
        debug("dbus has been called once, quitting")
        loop.quit()
    return True


class ComplianceChecker(dbus.service.Object):

    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)
        self.has_run = False
        #this will get set after first invocation
        self.last_status = None

    @dbus.service.signal(dbus_interface='com.redhat.SubscriptionManager.Compliance',  signature='i')
    def compliancechanged(self, status_code):
        debug("signal fired! code is " + str(status_code))

    @dbus.service.method(
        dbus_interface="com.redhat.SubscriptionManager.Compliance",
        out_signature='i')
    def check_compliance(self):
        """
        returns: 0 if not compliant, 1 if compliant, 2 if close to expiry
        """
        ret = check_compliance()
        if (ret != self.last_status):
            debug("Compliance status changed, fire signal")
            #we send the code out, but no one uses it at this time
            self.compliancechanged(ret)
        self.last_status = ret
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
        if compliant == RHSM_COMPLIANT:
            syslog.openlog("rhsm-complianced")
            syslog.syslog(syslog.LOG_NOTICE,
                    "This system is non-compliant. " +
                    "Please run subscription-manager-cli for more information.")
            return RHSM_COMPLIANT
        elif compliant == RHSM_WARNING:
            syslog.openlog("rhsm-complianced")
            syslog.syslog(syslog.LOG_NOTICE,
                    "This system's entitlements are about to expire. " +
                    "Please run subscription-manager-cli for more information.")
            return RHSM_WARNING
        elif compliant == RHN_CLASSIC:
            syslog.openlog("rhsm-complianced")
            syslog.syslog(syslog.LOG_NOTICE,
                          "This system is registered to RHN Classic")
            return RHN_CLASSIC
        
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
