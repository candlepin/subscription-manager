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
import gobject
import dbus
import dbus.service
import dbus.glib
import logging

import sys
sys.path.append("/usr/share/rhsm")

from subscription_manager.logutil import init_logger
init_logger()
log = logging.getLogger('rhsm-app.' + __name__)

from subscription_manager.injectioninit import init_dep_injection
init_dep_injection()

from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.branding import get_branding
from subscription_manager.injection import require, CERT_SORTER
from subscription_manager.hwprobe import ClassicCheck
from subscription_manager.i18n_optparse import OptionParser, \
    WrappedIndentedHelpFormatter, USAGE
from subscription_manager.cert_sorter import RHSM_VALID, \
        RHSM_EXPIRED, RHSM_WARNING, RHSM_PARTIALLY_VALID, \
        RHN_CLASSIC, RHSM_REGISTRATION_REQUIRED

import rhsm.config
CFG = rhsm.config.initConfig()

enable_debug = False


def debug(msg):
    if enable_debug:
        log.debug(msg)
        print msg


def in_warning_period(sorter):

    for entitlement in sorter.valid_entitlement_certs:
        if entitlement.is_expiring():
            return True
    return False


def pre_check_status(force_signal):
    if force_signal is not None:
        debug("forcing status signal from cli arg")
        return force_signal

    if ClassicCheck().is_registered_with_classic():
        debug("System is already registered to another entitlement system")
        return RHN_CLASSIC

    if not ConsumerIdentity.existsAndValid():
        debug("The system is not currently registered.")
        return RHSM_REGISTRATION_REQUIRED
    return None


def check_status(force_signal):
    pre_result = pre_check_status(force_signal)
    if pre_result is not None:
        return pre_result

    sorter = require(CERT_SORTER)

    return sorter.get_status_for_icon()


def check_if_ran_once(checker, loop):
    if checker.has_run:
        msg = "D-Bus com.redhat.SubscriptionManager.EntitlementStatus.check_status called once, exiting"
        debug(msg)
        loop.quit()
    return True


class StatusChecker(dbus.service.Object):

    def __init__(self, bus, keep_alive, force_signal, loop):
        name = dbus.service.BusName("com.redhat.SubscriptionManager", bus)
        dbus.service.Object.__init__(self, name, "/EntitlementStatus")
        self.has_run = False
        #this will get set after first invocation
        self.last_status = None
        self.keep_alive = keep_alive
        self.force_signal = force_signal
        self.loop = loop

    @dbus.service.signal(
        dbus_interface='com.redhat.SubscriptionManager.EntitlementStatus',
        signature='i')
    def entitlement_status_changed(self, status_code):
        log.info("D-Bus signal com.redhat.SubscriptionManager.EntitlementStatus.entitlement_status_changed emitted")
        debug("signal fired! code is " + str(status_code))

    #this is so we can guarantee exit after the dbus stuff is done, since
    #certain parts of that are async
    def watchdog(self):
        if not self.keep_alive:
            gobject.idle_add(check_if_ran_once, self, self.loop)

    @dbus.service.method(
        dbus_interface="com.redhat.SubscriptionManager.EntitlementStatus",
        out_signature='i')
    def check_status(self):
        """
        returns: 0 if entitlements are valid, 1 if not valid,
                 2 if close to expiry
        """
        log.info("D-Bus interface com.redhat.SubscriptionManager.EntitlementStatus.check_status called")
        ret = check_status(self.force_signal)
        if (ret != self.last_status):
            debug("Validity status changed, fire signal")
            #we send the code out, but no one uses it at this time
            self.entitlement_status_changed(ret)
        self.last_status = ret
        self.has_run = True
        self.watchdog()
        return ret

    @dbus.service.method(
            dbus_interface="com.redhat.SubscriptionManager.EntitlementStatus",
            in_signature='i')
    def update_status(self, status):
        log.info("D-Bus interface com.redhat.SubscriptionManager.EntitlementStatus.update_status called with status = %s" % status)
        pre_result = pre_check_status(self.force_signal)
        if pre_result is not None:
            status = pre_result
        if status != self.last_status:
            debug("Validity status changed, fire signal")
            self.entitlement_status_changed(status)
        self.last_status = status
        self.has_run = True
        self.watchdog()


def parse_force_signal(cli_arg):
    if cli_arg is None:
        return None

    cli_arg = cli_arg.lower().strip()

    if cli_arg == "valid":
        return RHSM_VALID
    elif cli_arg == "expired":
        return RHSM_EXPIRED
    elif cli_arg == "warning":
        return RHSM_WARNING
    elif cli_arg == "partial":
        return RHSM_PARTIALLY_VALID
    elif cli_arg == "classic":
        return RHN_CLASSIC
    elif cli_arg == "registration_required":
        return RHSM_REGISTRATION_REQUIRED
    else:
        sys.stderr.write("Invalid force option: %s\n" % cli_arg)
        sys.exit(-1)


def log_syslog(level, msg):
    syslog.openlog("rhsmd")
    syslog.syslog(level, msg)
    log.info("rhsmd: %s" % msg)
    if enable_debug:
        print msg


def main():

    log.info("rhsmd started")
    parser = OptionParser(usage=USAGE,
                          formatter=WrappedIndentedHelpFormatter())
    parser.add_option("-d", "--debug", dest="debug",
            help="Display debug messages", action="store_true", default=False)
    parser.add_option("-k", "--keep-alive", dest="keep_alive",
            help="Stay running (don't shut down after the first dbus call)",
            action="store_true", default=False)
    parser.add_option("-s", "--syslog", dest="syslog",
            help="Run standalone and log result to syslog",
            action="store_true", default=False)
    parser.add_option("-f", "--force-signal", dest="force_signal",
            help="Force firing of a signal " +
            "(valid, expired, warning, partial, classic or registration_required)")
    parser.add_option("-i", "--immediate", dest="immediate",
            action="store_true", default=False,
            help="Fire forced signal immediately (requires --force-signal)")

    options, args = parser.parse_args()

    force_signal = parse_force_signal(options.force_signal)

    if options.immediate and force_signal is None:
        sys.stderr.write("--immediate must be used with --force-signal\n")
        sys.exit(-2)

    global enable_debug
    enable_debug = options.debug

    # short-circuit dbus initialization
    if options.syslog:
        log.info("logging subscription status to syslog")
        status = check_status(force_signal)
        if status == RHSM_EXPIRED:
            log_syslog(syslog.LOG_NOTICE,
                       "This system is missing one or more subscriptions. " +
                        "Please run subscription-manager for more information.")
        elif status == RHSM_PARTIALLY_VALID:
            log_syslog(syslog.LOG_NOTICE,
                       "This system is missing one or more subscriptions " +
                       "to fully cover its products. " +
                       "Please run subscription-manager for more information.")
        elif status == RHSM_WARNING:
            log_syslog(syslog.LOG_NOTICE,
                       "This system's subscriptions are about to expire. " +
                       "Please run subscription-manager for more information.")
        elif status == RHN_CLASSIC:
            log_syslog(syslog.LOG_NOTICE,
                       get_branding().RHSMD_REGISTERED_TO_OTHER)
        elif status == RHSM_REGISTRATION_REQUIRED:
            log_syslog(syslog.LOG_NOTICE,
                       "In order for Subscription Manager to provide your " +
                       "system with updates, your system must be registered " +
                       "with the Customer Portal. Please enter your Red Hat " +
                       "login to ensure your system is up-to-date.")

        # Return an exit code for the program. having valid entitlements is
        # good, so it gets an exit status of 0.
        return status

    system_bus = dbus.SystemBus()
    loop = gobject.MainLoop()
    checker = StatusChecker(system_bus, options.keep_alive, force_signal, loop)

    if options.immediate:
        checker.entitlement_status_changed(force_signal)

    loop.run()


if __name__ == "__main__":
    main()
