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
import shutil
import config
import constants
import connection
import hwprobe
import optparse
import pprint
from optparse import OptionParser
from certlib import CertLib, ConsumerIdentity, ProductDirectory, EntitlementDirectory
import managerlib
import gettext
import facts
_ = gettext.gettext
from logutil import getLogger

log = getLogger(__name__)

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
        if ConsumerIdentity.exists():
            self.reload_cp_with_certs()
        else:
            self.cp = connection.UEPConnection(host=cfg['hostname'] or "localhost", 
                                               ssl_port=cfg['port'], handler="/candlepin")
        self.certlib = CertLib()

    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """

        self.parser.add_option("--debug", dest="debug",
                default=0, help="debug level")

    def _do_command(self):
        pass

    def reload_cp_with_certs(self):
        cert_file = ConsumerIdentity.certpath()
        key_file = ConsumerIdentity.keypath()
        self.cp = connection.UEPConnection(host=cfg['hostname'] or "localhost", 
                                           ssl_port=cfg['port'], handler="/candlepin", 
                                           cert_file=cert_file, key_file=key_file)

    def main(self):

        (self.options, self.args) = self.parser.parse_args()
        # we dont need argv[0] in this list...
        self.args = self.args[1:]

        # do the work, catch most common errors here:
        self._do_command()

class RegisterCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog register [OPTIONS]"
        shortdesc = "register the client to a Unified Entitlement Platform."
        desc = "register"

        CliCommand.__init__(self, "register", usage, shortdesc, desc)

        self.username = None
        self.password = None
        self.cp = connection.UEPConnection(host=cfg['hostname'] or "localhost", 
                                               ssl_port=cfg['port'], handler="/candlepin")
        self.parser.add_option("--username", dest="username", 
                               help="Specify a username")
        self.parser.add_option("--password", dest="password",
                               help="Specify a password")
        self.parser.add_option("--consumerid", dest="consumerid",
                               help="Register to an Existing consumer")
        self.parser.add_option("--autosubscribe", action='store_true',
                               help="Automatically subscribe this system to\
                                     compatible subscriptions.")
        self.parser.add_option("--force",  action='store_true', 
                               help="Register the system even if it is already registered")

    def _validate_options(self):
        if not (self.options.username and self.options.password) and not \
            self.options.consumerid:
            print (_("Error: username and password or consumerid are required to register,try --help.\n"))
            sys.exit(-1)

        if (self.options.username and self.options.password) and \
            self.options.consumerid:
            print(_("Error: username and password or consumerid are required, not both. try --help.\n"))
            sys.exit(-1)

        if ConsumerIdentity.exists() and not self.options.force:
            print(_("This system is already registered. Use --force to override"))
            sys.exit(1)

    def _get_register_info(self):
        stype = 'system'
        product = {"id":"1","label":"RHEL AP","name":"rhel"}
	fact_data = facts.get_facts()

        params = {
            "type":stype,
            "name":'admin',
            "facts": fact_data
        }
        return params

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()

        if self.options.consumerid:
            consumer = self.cp.getConsumerById(self.options.consumerid)

        elif ConsumerIdentity.exists() and self.options.force:
           try:
               consumer = self.cp.registerConsumer(self.options.username, self.options.password, self._get_register_info())
               consumerid = check_registration()['uuid']
           except connection.RestlibException, re:
               systemExit(-1, re.msg)
           try:
               self.cp.unregisterConsumer(consumerid)
               log.info("--force specified. Successfully Unsubscribed the old consumer.")
           except:
                log.error("Unable to unregister with consumer %s" % consumerid)
        else:
            try:
                consumer = self.cp.registerConsumer(self.options.username,
                        self.options.password, self._get_register_info())
            except connection.RestlibException, re:
                systemExit(-1, re.msg)

        managerlib.persist_consumer_cert(consumer)
        self.reload_cp_with_certs()
        if self.options.autosubscribe:
            # try to auomatically bind products
            for pname, phash in managerlib.getInstalledProductHashMap().items():
                try:
                   print "Bind Product ", pname,phash
                   self.cp.bindByProduct(consumer['uuid'], phash)
                   log.info("Automatically subscribe the machine to product %s " % pname)
                except:
                   log.warning("Warning: Unable to auto subscribe the machine to %s" % pname)
            self.certlib.update()

class UnRegisterCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog unregister [OPTIONS]"
        shortdesc = "unregister the client from a Unified Entitlement Platform."
        desc = "unregister"

        CliCommand.__init__(self, "unregister", usage, shortdesc, desc)

    def _validate_options(self):
        pass

    def _do_command(self):
        if not ConsumerIdentity.exists():
            print(_("This system is currently not registered."))
            sys.exit(1)

        try:
           consumer = check_registration()['uuid']
           self.cp.unregisterConsumer(consumer)
           # clean up stale consumer/entitlement certs
           shutil.rmtree("/etc/pki/consumer/")
           shutil.rmtree("/etc/pki/entitlement/")
           log.info("Successfully Unsubscribed the client from Entitlement Platform.")
        except connection.RestlibException, re:
           log.error("Error: Unable to UnRegister the system: %s" % re)
           systemExit(-1, re.msg)
        except:
            log.error("Error: Unable to UnRegister the system")

class SubscribeCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog subscribe [OPTIONS]"
        shortdesc = "subscribe the registered user to a specified product or regtoken."
        desc = "subscribe"
        CliCommand.__init__(self, "subscribe", usage, shortdesc, desc)

        self.product = None
        self.regtoken = None
        self.substoken = None
        self.parser.add_option("--product", dest="product", action='append',
                               help="product ID")
        self.parser.add_option("--regtoken", dest="regtoken", action='append',
                               help="regtoken")
        self.parser.add_option("--pool", dest="pool", action='append',
                               help="Subscription Pool Id")
        self.parser.add_option("--email", dest="email", action='store',
                               help=_("Optional email address to notify when "
                               "token actication is complete. Used with "
                               "--regtoken only"))
        self.parser.add_option("--lang", dest="lang", action='store',
                               help=_("Optional language to use for email "
                               "notification when token actication is "
                               "complete. Used with --regtoken and --email "
                               "only"))

    def _validate_options(self):
        if not (self.options.regtoken or self.options.product or self.options.pool):
            print _("Error: Need either --product or --regtoken, Try --help")
            sys.exit(-1)

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        consumer = check_registration()['uuid']
        try:
            if self.options.product:
                for product in self.options.product:
                    bundles = self.cp.bindByProduct(consumer, product)
                    log.info("Info: Successfully subscribed the machine to product %s" % product)

            if self.options.regtoken:
                for regnum in self.options.regtoken:
                    bundles = self.cp.bindByRegNumber(consumer, regnum,
                            self.options.email, self.options.lang)
                    log.info("Info: Successfully subscribed the machine to registration token %s" % regnum)

            if self.options.pool:
                for pool in self.options.pool:
                    bundles = self.cp.bindByEntitlementPool(consumer, pool)
                    log.info("Info: Successfully subscribed the machine the Entitlement Pool %s" % pool)
            self.certlib.update()
        except connection.RestlibException, re:
            log.error(re)
            systemExit(-1, re.msg)
        except Exception, e:
            log.error("Unable to subscribe: %s" % e)
            systemExit(-1, msgs=e)

class UnSubscribeCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog unsubscribe [OPTIONS]"
        shortdesc = "unsubscribe the registered user from all or specific subscriptions."
        desc = "unsubscribe"
        CliCommand.__init__(self, "unsubscribe", usage, shortdesc, desc)

        self.serial_numbers = None
        self.parser.add_option("--serial", dest="serial",
                               help="Certificate serial to unsubscribe")

    def _validate_options(self):
        CliCommand._validate_options(self)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer = check_registration()['uuid']
        try:
            if self.options.serial:
                self.cp.unBindBySerialNumber(consumer, self.options.serial)
                log.info("This machine has been Unsubscribed from subcription with Serial number %s" % (self.options.serial))
            else:
                self.cp.unbindAll(consumer)
                log.info("Warning: This machine has been unsubscribed from all its subscriptions as per user request.")
            self.certlib.update()
        except connection.RestlibException, re:
            log.error(re)
            systemExit(-1, re.msg)
        except Exception,e:
            log.error("Unable to perform unsubscribe due to the following exception \n Error: %s" % e)
            systemExit(-1, msgs=e)



class ListCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog list [OPTIONS]"
        shortdesc = "list available or consumer subscriptions for registered user"
        desc = "list available or consumed Entitlement Pools for this system."
        CliCommand.__init__(self, "list", usage, shortdesc, desc)
        self.available = None
        self.consumed = None
        self.parser.add_option("--available", action='store_true',
                               help="available")
        self.parser.add_option("--consumed", action='store_true',
                               help="consumed")


    def _validate_options(self):
        pass

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        consumer = check_registration()['uuid']
        if not (self.options.available or self.options.consumed):
           iproducts = managerlib.getInstalledProductStatus()
           if not len(iproducts):
               print("No installed Products to list")
               sys.exit(0)
           print """+-------------------------------------------+\n    Installed Product Status\n+-------------------------------------------+"""
           for product in iproducts:
               print constants.installed_product_status % product

        if self.options.available:
           epools = managerlib.getAvailableEntitlementsCLI(self.cp, consumer)
           if not len(epools):
               print("No Available subscription pools to list")
               sys.exit(0)
           print """+-------------------------------------------+\n    Available Subscriptions\n+-------------------------------------------+\n"""
           for data in epools:
               print constants.available_subs_list % (data['productName'], 
                                                      data['productId'], 
                                                      data['id'], 
                                                      data['quantity'], 
                                                      data['endDate'])

        if self.options.consumed:
           cpents = managerlib.getConsumedProductEntitlements()
           if not len(cpents):
               print("No Consumed subscription pools to list")
               sys.exit(0)
           print """+-------------------------------------------+\n    Consumed Product Subscriptions\n+-------------------------------------------+\n"""
           for product in cpents:
                print constants.consumed_subs_list % product 


# taken wholseale from rho...
class CLI:
    def __init__(self):

        self.cli_commands = {}
        for clazz in [ RegisterCommand, UnRegisterCommand, ListCommand, SubscribeCommand,\
                       UnSubscribeCommand]:
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
            #print(" %-25s" % cmd.parser.print_help())
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
        if len(sys.argv) < 2 or not self._find_best_match(sys.argv):
            self._usage()
            sys.exit(0)

        cmd = self._find_best_match(sys.argv)
        if not cmd:
            self._usage()
            sys.exit(0)

        cmd.main()

def systemExit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(unicode(msg).encode("utf-8") + '\n')
    sys.exit(code)

def check_registration():
    if not ConsumerIdentity.exists():
        needToRegister = \
            _("Error: You need to register this system by running " \
            "`register` command before using this option.")
        print needToRegister
        sys.exit(1)
    consumer = ConsumerIdentity.read()
    consumer_info = {"consumer_name" : consumer.getConsumerName(),
                     "uuid" : consumer.getConsumerId(),
                     "user_account"  : consumer.getUser()
                    }
    return consumer_info

if __name__ == "__main__":
    CLI().main()
