#!/usr/bin/python
#
# Subscription manager commandline utility. This script is a modified version of
# cp_client.py from candlepin scripts
#
# Copyright (c) 2010 Red Hat, Inc.
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
import config
import connection
import hardware
import optparse
from optparse import OptionParser

import gettext
_ = gettext.gettext

cfg = config.initConfig()

class CliCommand(object):
    """ Base class for all sub-commands. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
            description=None):
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.debug = 0
        self.parser = OptionParser(usage=usage, description=description)
        self._add_common_options()
        self.name = name

        self.cp = connection.UEPConnection(host=cfg['hostname'] or "localhost",\
                             port=cfg['port'] or "8080", handler="/candlepin")


    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """

#        self.parser.add_option("--log", dest="log_file", metavar="FILENAME",
#                help="log file name (will be overwritten)")
        self.parser.add_option("--debug", dest="debug",
                default=0, help="debug level")

    def _do_command(self):
        pass

    def main(self):

        (self.options, self.args) = self.parser.parse_args()
        # we dont need argv[0] in this list...
        self.args = self.args[1:]

        # do the work, catch most common errors here:
        self._do_command()

class RegisterCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog register"
        shortdesc = "register"
        desc = "register"

        CliCommand.__init__(self, "register", usage, shortdesc, desc)

        self.username = None
        self.password = None
        self.system = None
        self.parser.add_option("--username", dest="username", 
                               help="username")
        self.parser.add_option("--password", dest="password",
                               help="password")

    def _validate_options(self):
        CliCommand._validate_options(self)

    def _get_register_info(self):
        stype = {'label':'system'}
        product = {"id":"1","label":"RHEL AP","name":"rhel"}
        facts = hardware.read_dmi()
        params = {
                "type":stype,
                "name":'admin',
                "facts":facts,
        }
        print params
        return params

    def _write_consumer_cert(self, consumerinfo):
        if not os.path.isdir("/etc/pki/consumer/"):
            os.mkdir("/etc/pki/consumer/")
        f = open("/etc/pki/consumer/cert.pem", "w")
        #TODO: this will a pki cert in future
        f.write(consumerinfo)
        f.close()

    def _do_command(self):
        """
        Executes the command.
        """

        consumer = self.cp.registerConsumer(self.options.username, self.options.password, self._get_register_info())
        self._write_consumer_cert(consumer['uuid'])

class SubscribeCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog subscribe --product [product_label] --regtoken [regtoken] --substoken [subscription-number]"
        shortdesc = "subscribe"
        desc = "subscribe"
        CliCommand.__init__(self, "subscribe", usage, shortdesc, desc)

        self.product = None
        self.regtoken = None
        self.substoken = None
        self.parser.add_option("--product", dest="product",
                               help="product")
        self.parser.add_option("--regtoken", dest="regtoken",
                               help="regtoken")
        self.parser.add_option("--substoken", dest="substoken",
                               help="substoken")

    def _validate_options(self):
        if self.options.regtoken and self.options.product:
            print "Need either --product or --regtoken, not both"
            sys.exit()

        CliCommand._validate_options(self)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer = check_registration()
        if self.options.product:
            print self.cp.bindByProduct(consumer, self.options.product)
        if self.options.regtoken:
            print self.cp.bindRegToken(consume, self.options.regtoken)

class UnSubscribeCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog unsubscribe --serialnumbers [serial1,serial2,serial3]"
        shortdesc = "unsubscribe"
        desc = "unsubscribe"
        CliCommand.__init__(self, "unsubscribe", usage, shortdesc, desc)

        self.serial_numbers = None
        self.parser.add_option("--serialnumbers", dest="serial_numbers",
                               help="serial_numbers")

    def _validate_options(self):
        CliCommand._validate_options(self)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer = check_registration()

        if not self.options.serial_numbers:
            print self.cp.unbindAll(consumer)

        if self.options.serial_numbers:
            print self.cp.unBindBySerialNumbers(consumer, self.options.serial_numbers)

class SyncCertificatesCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog syncCertificates "
        shortdesc = "syncCertificates"
        desc = "syncCertificates"
        CliCommand.__init__(self, "syncCertificates", usage, shortdesc, desc)


    def _validate_options(self):
        CliCommand._validate_options(self)

    def _do_command(self):
        """
        Executes the command.
        """
        print self.cp.syncCertificates(consumer_uuid, [])

class GetEntitlementPoolsCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog list --available --consumed"
        shortdesc = "listEntitlementPools"
        desc = "list available or consumed Entitlement Pools for this system."
        CliCommand.__init__(self, "list", usage, shortdesc, desc)

    def _validate_options(self):
        CliCommand._validate_options(self)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer = check_registration()
        print self.cp.getEntitlementPools(consumer)


# taken wholseale from rho...
class CLI:
    def __init__(self):

        self.cli_commands = {}
        for clazz in [ RegisterCommand, SubscribeCommand,\
                       UnSubscribeCommand,GetEntitlementPoolsCommand]:
            cmd = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_commands[cmd.name] = cmd 


    def _add_command(self, cmd):
        self.cli_commands[cmd.name] = cmd

    def _usage(self):
        print "\nUsage: %s [options] MODULENAME --help\n" % os.path.basename(sys.argv[0])
        print "Supported modules:\n"

        # want the output sorted
        items = self.cli_commands.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
        print("")

    def _find_best_match(self, args):
        """
        Returns the subcommand class that best matches the subcommand specified
        in the argument list. For example, if you have two commands that start
        with auth, 'auth show' and 'auth'. Passing in auth show will match
        'auth show' not auth. If there is no 'auth show', it tries to find
        'auth'.

        This function ignores the arguments which begin with --
        """
        possiblecmd = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        if not possiblecmd:
            return None

        cmd = None
        key = " ".join(possiblecmd)
        if self.cli_commands.has_key(" ".join(possiblecmd)):
            cmd = self.cli_commands[key]

        i = -1
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            if self.cli_commands.has_key(key):
                cmd = self.cli_commands[key]
            i -= 1

        return cmd

    def main(self):
        #self._check_registration()
        if len(sys.argv) < 2 or not self._find_best_match(sys.argv):
            self._usage()
            sys.exit(1)

        cmd = self._find_best_match(sys.argv)
        if not cmd:
            self._usage()
            sys.exit(1)

        cmd.main()

def check_registration():
    if not os.access("/etc/pki/consumer/cert.pem", os.F_OK):
        needToRegister = \
            _("Error: You need to register this system by running " \
            "`register` command before using this option.")
        print needToRegister
        sys.exit(1)
    return open("/etc/pki/consumer/cert.pem").read()


if __name__ == "__main__":
    CLI().main()
