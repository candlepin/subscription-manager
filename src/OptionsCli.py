#!/usr/bin/python
#
# Subscription Manager commandline utility

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

import os
import sys
import getpass
import config
from optparse import Option, OptionParser, OptionGroup

import Connection
import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

cfg = config.initConfig()

def generateOptions():
    parser = OptionParser(usage="%prog [OPTION]")
    group = OptionGroup(parser, "Registration Options Group")
    group.add_option(  '--register',          action='store_true',
        help='Register the system to Entitlement Platform.'),
    group.add_option('--username',          action='store',
        help='User account to register the system.')
    group.add_option(  '--password',          action='store',
        help='Password for the user account')
    parser.add_option_group(group)

    group = OptionGroup(parser, "List Options Group")
    group.add_option(  '--list-available',          action='store_true',
        help='List all available Subscriptions for this system.'),
    group.add_option(  '--list-consumed',          action='store_true',
        help='List all consumed Subscriptions by this system.')
    parser.add_option_group(group)

    group = OptionGroup(parser, "Subscribe Options Group")
    group.add_option('--subscribe', action='store_true',
        help='Subscribes the client to a product/serial_number or registration token'),
    group.add_option('--product', dest='bind_product', 
        metavar='product_label', action='store',
        help='Subscribe the client to a specific product label'),
    group.add_option('--serial-number', dest='bind_serial', 
        metavar='serial_number', action='store',
        help='Subscribe the client to a specific subscription serial number'),
    group.add_option('--reg-token', dest='bind_regtoken', 
        metavar='registration_token', action='store',
        help='Subscribe the client to a specific Registration Token'),
    parser.add_option_group(group)

    group = OptionGroup(parser, "UnSubscribe Options Group")
    group.add_option(    '--unsubscribe', action='store_true',
        help='UnSubscribe the client from specific or all Subscription'),
    group.add_option(    '--serial-number', action='store',
        metavar='[num1,num2..]',
        help='UnSubscribe the client from specifie Subscription serial numbers'),
    group.add_option(    '--all', action='store_true',
        help='UnSubscribe the client from all Product Subscription'), 
    parser.add_option_group(group)

    group = OptionGroup(parser, "Common Options")
    group.add_option('-v', '--verbose', action='store_true',
        help='verbose output')
    parser.add_option_group(group)
    return parser

def validateOptions(parser):
    pass

class ManagerCLI:
    """
    A Commandline subscription Manager tool
    """
    def __init__(self):
        self.optParser = generateOptions()
        self.options = None
        self.args = None

    def initialize(self):
        (self.options, self.args) = self.optParser.parse_args()

    def run(self):
        self.initialize()
        uep = Connection.UEPConnection(cfg['baseUrl'] or "localhost")

        if (self.options.username and self.options.password) and \
           not self.options.register:
            print _("\nError: `--register` is required with username and password to register a system.\n")
            sys.exit(-1)

        if self.options.register:
            if not (self.options.username and self.options.password):
                print _("\nError: A username and password are required "\
                    "to register a system.\n")
                sys.exit(-1)
            info = getRegisterInfo()
            consumer = uep.registerConsumer(self.options.username,\
                           self.options.password, info=info)
        print consumer

        if self.options.list_available:
            # Get list of available Entitlement Pools
            self.__registered()
            print uep.getEntitlementPools(consumer['uuid'])
            sys.exit(0)

        if self.options.list_consumed:
            pass
        if self.options.subscribe and not (self.options.bind_product \
           or self.options.bind_regtoken \
           or self.options.bind_serial):
           sys.stderr.write( _("\nError: A --product or --serial-number or --regtoken is required with --subscribe.\n"))
           sys.exit(0)

        if self.options.subscribe and self.options.bind_product:
            self.__registered()
            try:
                print uep.bindByProduct(consumer['uuid'], self.options.bind_product)
                print uep.syncCertificates(consumer['uuid'], [])
                sys.exit(0)
            except Exception, e:
                sys.stderr.write(_("Error: %s - Unable to bind the product \'%s\' \n") % (e, self.options.bind_product))

        if self.options.bind_regtoken:
            self.__registered()
            try:
                print uep.bindByProduct(consumer['uuid'], self.options.bind_regtoken)
                print uep.syncCertificates(consumer['uuid'], [])

            except Exception, e:
                sys.stderr.write(_("Error: %s - Unable to bind the registration token \'%s\'\n") % (e, self.options.bind_regtoken))
        if self.options.unsubscribe_serial:
            self.__registered()
            print uep.unBindBySerialNumbers(consumer['uuid'], self.options.unbind_serial)
            print uep.syncCertificates(consumer['uuid'], [])

        if self.options.unsubscribeall:
            self.__registered()
            print uep.unbindAll(consumer['uuid'])
            print uep.syncCertificates(consumer['uuid'], [])

    @staticmethod
    def __registered():
        needToRegister=None
        if not os.access("/etc/pki/consumer/cert.pem", os.F_OK):
            needToRegister = \
                _("You need to register this system by running with " \
                "`--register` option.")
            print needToRegister
            sys.exit(1)

def getRegisterInfo():
    stype = {'label':'system'}
    product = {"id":"1","label":"RHEL AP","name":"rhel"}
    facts = {"metadata": {
            "entry":[{"key":"arch","value":"i386"},
                     {"key":"cpu", "value": "Intel" },
                     {"key":"cores", "value":4}]
            }
    }
    params = {
            "type":stype,
            "name":'admin',
            "facts":facts,
    }
    return params

def getProductInfo():
    pass

if __name__=='__main__':
    subs =  ManagerCLI()
    subs.run()
