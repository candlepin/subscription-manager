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
import logging
import socket
import getpass
import rhsm.config
import constants
import dbus
import datetime
from time import strftime, strptime, localtime
import rhsm.connection as connection
from i18n_optparse import OptionParser
from certlib import CertLib, ConsumerIdentity
import managerlib
from facts import Facts
from M2Crypto import X509
from M2Crypto import SSL

import gettext
_ = gettext.gettext


log = logging.getLogger('rhsm-app.' + __name__)

cfg = rhsm.config.initConfig()

def handle_exception(msg, ex):
    log.error(msg)
    log.exception(ex)
    if isinstance(ex, socket.error):
        print _('Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.')
        sys.exit(-1)
    elif isinstance(ex, connection.NetworkException):
        # NOTE: yes this looks a lot like the socket error, but I think these
        # were actually intended to display slightly different messages:
        print _("Network error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information.")
        sys.exit(-1)
    elif isinstance(ex, connection.RemoteServerException):
        # This is what happens when there's an issue with the server on the other side of the wire
        print _("Remote server error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information.")
        sys.exit(-1)
    elif isinstance(ex, connection.RestlibException):
        print _(ex.msg)
        sys.exit(-1)
    elif isinstance(ex, SSL.Checker.WrongHost):
        print str(ex)
        sys.exit(-1)
    elif isinstance(ex, connection.BadCertificateException):
        print _("Bad CA certificate: %s") % ex.cert_path
        sys.exit(-1)
    else:
        systemExit(-1, ex)


def autosubscribe(cp, consumer, certlib):
    # try to auomatically bind products
    products = managerlib.getInstalledProductHashMap()
    try:
        ents = cp.bindByProduct(consumer, products.values())
        certlib.update()

        installed_status = managerlib.getInstalledProductStatus()

        log.info("Automatically subscribed to products: %s " \
                % ", ".join(products.keys()))
        print _("Installed Products:")
        for prod_status in installed_status:
            print ("   %s - %s" % (prod_status[0], prod_status[1]))
    except Exception, e:
        log.exception(e)
        log.warning("Warning: Unable to auto subscribe to %s" \
                % ", ".join(products.keys()))


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

        self.proxy_url = None
        self.proxy_hostname = None
        self.proxy_port = None

    def _get_dbus_iface(self):
        bus = dbus.SystemBus()
        compliance_obj = bus.get_object('com.redhat.SubscriptionManager',
                          '/Compliance')
        compliance_iface = dbus.Interface(compliance_obj,
                            dbus_interface='com.redhat.SubscriptionManager.Compliance')
        return compliance_iface

    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """

        self.parser.add_option("--debug", dest="debug",
                               default=0, help=_("debug level"))
        self.parser.add_option("--proxy", dest="proxy_url",
                               default=None, help=_("proxy url in the form of proxy_hostname:proxy_port"))
        self.parser.add_option("--proxyuser", dest="proxy_user",
                                default=None, help=_("user for http proxy with basic authentication"))
        self.parser.add_option("--proxypassword", dest="proxy_password",
                                default=None, help=_("password for http proxy with basic authentication"))

    def _do_command(self):
        pass

    def assert_should_be_registered(self):
        if not ConsumerIdentity.exists():
            print (_("Consumer not registered. Please register using --username and --password"))
            sys.exit(-1)

    def main(self, args=None):

        # In testing we sometimes specify args, otherwise use the default:
        if not args:
            args = sys.argv[1:]

        (self.options, self.args) = self.parser.parse_args(args)

        # we dont need argv[0] in this list...
        self.args = self.args[1:]

        proxy_hostname = None
        proxy_port = None

        self.proxy_hostname = cfg.get('server', 'proxy_hostname')
        self.proxy_port = cfg.get('server', 'proxy_port')
        self.proxy_user = cfg.get('server', 'proxy_user')
        self.proxy_password = cfg.get('server', 'proxy_password')

        # support foo.example.com:3128 format
        if self.options.proxy_url:
            parts = self.options.proxy_url.split(':')
            self.proxy_hostname = parts[0]
            # no ':'
            if len(parts) > 1:
                self.proxy_port = parts[1]
            else:
                # if no port specified, use the one from the config, or fallback to the default
                self.proxy_port = cfg.get('server', 'proxy_port') or rhsm.config.DEFAULT_PROXY_PORT

        if self.options.proxy_user:
            self.proxy_user = self.options.proxy_user
        if self.options.proxy_password:
            self.proxy_password = self.options.proxy_password

        # Create a connection using the default configuration:
        cert_file = ConsumerIdentity.certpath()
        key_file = ConsumerIdentity.keypath()

        self.cp = connection.UEPConnection(cert_file=cert_file, key_file=key_file,
                                           proxy_hostname=self.proxy_hostname,
                                           proxy_port=self.proxy_port,
                                           proxy_user=self.proxy_user,
                                           proxy_password=self.proxy_password)

        self.certlib = CertLib(uep=self.cp)

        # do the work, catch most common errors here:
        try:
            self._do_command()
        except X509.X509Error, e:
            log.error(e)
            print _('Consumer certificates corrupted. Please reregister.')


class UserPassCommand(CliCommand):

    """
    Abstract class for commands that require a username and password
    """

    def __init__(self, name, usage=None, shortdesc=None,
            description=None):
        super(UserPassCommand, self).__init__(name, usage, shortdesc,
                description)
        self._username = None
        self._password = None

        self.parser.add_option("--username", dest="username",
                               help=_("specify a username"))
        self.parser.add_option("--password", dest="password",
                               help=_("specify a password"))

    @staticmethod
    def _get_username_and_password(username, password):
        """
        Safely get a username and password from the tty, without echoing.
        if either username or password are provided as arguments, they will
        not be prompted for.
        """

        if not username:
            while not username:
                username = raw_input(_("Username: "))
        if not password:
            while not password:
                password = getpass.getpass(_("Password: "))

        return (username, password)

    # lazy load the username and password, prompting for them if they weren't
    # given as options. this lets us not prompt if another option fails,
    # or we don't need them.
    @property
    def username(self):
        if not self._username:
            (self._username, self._password) = self._get_username_and_password(
                    self.options.username, self.options.password)
        return self._username

    @property 
    def password(self):
        if not self._password:
            (self._username, self._password) = self._get_username_and_password(
                    self.options.username, self.options.password)
        return self._password
    

class CleanCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog clean [OPTIONS]"
        shortdesc = _("removes all local consumer data, does not effect the server")
        desc = shortdesc

        CliCommand.__init__(self, "clean", usage, shortdesc, desc)

        # remove these options as per bz #664581
        self.parser.remove_option("--proxy")
        self.parser.remove_option("--proxyuser")
        self.parser.remove_option("--proxypassword")

    def _do_command(self):
        managerlib.delete_consumer_certs()
        log.info("Cleaned local data")
        print (_("All local data removed"))


class RefreshCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog refresh [OPTIONS]"
        shortdesc = _("pulls the latest entitlement data from the server")
        desc = shortdesc

        CliCommand.__init__(self, "refresh", usage, shortdesc, desc)

    def _do_command(self):
        check_registration()
        try:
            self.certlib.update()
            log.info("Refreshed local data")
            print (_("All local data refreshed"))
        except connection.RestlibException, re:
            log.error(re)
            systemExit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Unable to perform refresh due to the following exception \n Error: %s") % e, e)


class IdentityCommand(UserPassCommand):

    def __init__(self):
        usage = "usage: %prog identity [OPTIONS]"
        shortdesc = _("request a new identity certficate for this machine")
        desc = shortdesc

        super(IdentityCommand, self).__init__("identity", usage, shortdesc,
                desc)

        self.parser.add_option("--regenerate", action='store_true',
                               help=_("request a new certificate be generated"))
        self.parser.add_option("--force", action='store_true',
                               help=_("force certificate regeneration (requires username and password)"))

    def _validate_options(self):
        self.assert_should_be_registered()
        if not ConsumerIdentity.existsAndValid():
            print (_("Consumer identity either does not exist or is corrupted. Try register --help"))
            sys.exit(-1)
        if self.options.force and not self.options.regenerate:
            print(_("--force can only be used with --regenerate"))
            sys.exit(-1)
        if (self.options.username or self.options.password) and \
                not self.options.force:
            print(_("--username and --password can only be used with --force"))
            sys.exit(-1)

    def _do_command(self):

        self._validate_options()

        try:
            consumer =  check_registration()
            consumerid = consumer['uuid']
            consumer_name = consumer['consumer_name']
            if not self.options.regenerate:
                print _('Current identity is: %s name: %s') % (consumerid, consumer_name)
            else:
                if self.options.force:
                    self.cp = connection.UEPConnection(username=self.username,
                                                       password=self.password,
                                                       proxy_hostname=self.proxy_hostname,
                                                       proxy_port=self.proxy_port,
                                                       proxy_user=self.proxy_user,
                                                       proxy_password=self.proxy_password)
                consumer = self.cp.regenIdCertificate(consumerid)
                managerlib.persist_consumer_cert(consumer)

            log.info("Successfully generated a new identity from Entitlement Platform.")
        except connection.RestlibException, re:
            log.exception(re)
            log.error("Error: Unable to generate a new identity for the system: %s" % re)
            systemExit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to generate a new identity for the system"), e)


class RegisterCommand(UserPassCommand):

    def __init__(self):
        usage = "usage: %prog register [OPTIONS]"
        shortdesc = _("register the client to RHN")
        desc = "register"

        super(RegisterCommand, self).__init__("register", usage, shortdesc,
                desc)

        self.parser.add_option("--type", dest="consumertype", default="system",
                               help=_("the type of consumer to register. Defaults to system"))
        self.parser.add_option("--name", dest="consumername",
                               help=_("name of the consumer to register. Defaults to the hostname."))
        self.parser.add_option("--consumerid", dest="consumerid",
                               help=_("register to an existing consumer"))
        self.parser.add_option("--autosubscribe", action='store_true',
                               help=_("automatically subscribe this system to\
                                     compatible subscriptions."))
        self.parser.add_option("--force", action='store_true',
                               help=_("register the system even if it is already registered"))
        self.facts = Facts()

    def _validate_options(self):
        if ConsumerIdentity.exists() and not self.options.force:
            print(_("This system is already registered. Use --force to override"))
            sys.exit(1)
        elif (self.options.consumername == ''):
            print(_("Error: consumer name can not be empty."))
            sys.exit(-1)

    def _do_command(self):
        """
        Executes the command.
        """
        # Always warn the user if registered to old RHN 
        if managerlib.is_registered_with_classic():
            print constants.RHN_CLASSIC_WARNING

        self._validate_options()

        # Set consumer's name to hostname by default:
        consumername = self.options.consumername
        if consumername == None:
            consumername = socket.gethostname()

        admin_cp = connection.UEPConnection(username=self.username,
                                            password=self.password,
                                            proxy_hostname=self.proxy_hostname,
                                            proxy_port=self.proxy_port,
                                            proxy_user=self.proxy_user,
                                            proxy_password=self.proxy_password)

        if ConsumerIdentity.exists() and self.options.force:
            # First let's try to un-register previous consumer. This may fail
            # if consumer has already been deleted so we will continue even if
            # errors are encountered.
            if ConsumerIdentity.existsAndValid():
                old_uuid = ConsumerIdentity.read().getConsumerId()
                try:
                    managerlib.unregister(self.cp, old_uuid)
                    log.info("--force specified, un-registered old consumer: %s" % old_uuid)
                    print(_("The system with UUID %s has been unregistered") % old_uuid)
                except Exception, e:
                    log.error("Unable to un-register consumer: %s" % old_uuid)
                    log.exception(e)

        # Proceed with new registration:
        try:
            if self.options.consumerid:
            #TODO remove the username/password
                consumer = admin_cp.getConsumer(self.options.consumerid,
                        self.username, self.password)
            else:
                consumer = admin_cp.registerConsumer(name=consumername,
                                                     type=self.options.consumertype,
                                                     facts=self.facts.get_facts())
        except connection.RestlibException, re:
            log.exception(re)
            systemExit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error during registration: %s") % e, e)

        managerlib.persist_consumer_cert(consumer)

        if self.options.autosubscribe:
            autosubscribe(admin_cp, consumer['uuid'], self.certlib)
        if self.options.consumerid:
            self.certlib.update()

        #fire a check_compliance event
        dbus_proxy_iface = self._get_dbus_iface()
        dbus_proxy_iface.check_compliance()

class UnRegisterCommand(CliCommand):

    def __init__(self):
        usage = "usage: %prog unregister [OPTIONS]"
        shortdesc = _("unregister the client from RHN")
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
            managerlib.unregister(self.cp, consumer, False)
        except Exception, e:
            handle_exception("Unregister failed", e)

        #fire a check_compliance event
        dbus_proxy_iface = self._get_dbus_iface()
        dbus_proxy_iface.check_compliance()

        print(_("System has been un-registered."))

class ActivateCommand(CliCommand):

    def __init__(self):
        usage = "usage: %prog activate [OPTIONS]"
        shortdesc = _("activate the registered user to a specified product")
        desc = "activate"
        CliCommand.__init__(self, "activate", usage, shortdesc, desc)

        self.parser.add_option("--email", dest="email", action='store',
                               help=_("optional email address to notify when "
                               "token activation is complete."))
        self.parser.add_option("--locale", dest="locale", action='store',
                               help=_("optional language to use for email "
                               "notification when token activation is "
                               "complete. Used with --email only. Examples: en-us, de-de"))

    def _validate_options(self):
        pass

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        consumer = check_registration()['uuid']

        try:
            # update facts first, if we need to
            facts = Facts()

            if facts.delta():
                self.cp.updateConsumerFacts(consumer, facts.get_facts())

            self.cp.activateMachine(consumer, self.options.email, self.options.locale)

        except Exception, e:
            handle_exception("Unable to activate: %s" % e, e)

class SubscribeCommand(CliCommand):

    def __init__(self):
        usage = "usage: %prog subscribe [OPTIONS]"
        shortdesc = _("subscribe the registered machine to a specified product")
        desc = "subscribe"
        CliCommand.__init__(self, "subscribe", usage, shortdesc, desc)

        self.product = None
        self.substoken = None
        self.parser.add_option("--pool", dest="pool", action='append',
                               help=_("subscription pool id"))
        self.parser.add_option("--auto", action='store_true',
                               help=_("automatically subscribe this system to\
                                     compatible subscriptions."))

    def _validate_options(self):
        if not (self.options.pool or self.options.auto):
            print _("Error: Need to supply --pool or --auto.")
            sys.exit(-1)
        if self.options.pool and self.options.auto:
            print _("Error: Only one of --pool or --auto may be used.")
            sys.exit(-1)

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        consumer = check_registration()['uuid']
        try:
            # update facts first, if we need to
            facts = Facts()

            if facts.delta():
                self.cp.updateConsumerFacts(consumer, facts.get_facts())

            if self.options.pool:
                for pool in self.options.pool:
                    try:
                        # odd html strings will cause issues, reject them here.
                        if (pool.find("#") >= 0):
                            systemExit(-1, _("Please enter a valid numeric pool id."))
                        self.cp.bindByEntitlementPool(consumer, pool)
                        log.info("Info: Successfully subscribed the machine the Entitlement Pool %s" % pool)
                    except connection.RestlibException, re:
                        log.exception(re)
                        if re.code == 403:
                            print re.msg  #already subscribed.
                        elif re.code == 400:
                            print re.msg #no such pool.
                        else:
                            systemExit(-1, re.msg) #some other error.. don't try again
            # must be auto
            else:
                autosubscribe(self.cp, consumer, self.certlib)

            result = self.certlib.update()
            if result[1]:
                print 'Entitlement Certificate(s) update failed due to the following reasons:'
                for e in result[1]:
                    print '\t-', ' '.join(str(e).split('-')[1:]).strip()
            dbus_proxy_iface = self._get_dbus_iface()
            dbus_proxy_iface.check_compliance()

        except Exception, e:
            handle_exception("Unable to subscribe: %s" % e, e)

class UnSubscribeCommand(CliCommand):

    def __init__(self):
        usage = "usage: %prog unsubscribe [OPTIONS]"
        shortdesc = _("unsubscribe the registered user from all or specific subscriptions")
        desc = "unsubscribe"
        CliCommand.__init__(self, "unsubscribe", usage, shortdesc, desc)

        self.serial_numbers = None
        self.parser.add_option("--serial", dest="serial",
                               help=_("Certificate serial to unsubscribe"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("Unsubscribe from all subscriptions"))


    def _validate_options(self):
        CliCommand._validate_options(self)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer = check_registration()['uuid']
        try:
            if self.options.all:
                self.cp.unbindAll(consumer)
                log.info("Warning: This machine has been unsubscribed from all its subscriptions as per user request.")
            elif self.options.serial:
                if not self.options.serial.isdigit():
                    systemExit(-1, "'%s' is not a valid serial number" % self.options.serial)
                else:
                    self.cp.unbindBySerial(consumer, self.options.serial)
                    log.info("This machine has been Unsubscribed from subcription with Serial number %s" % (self.options.serial))
            else:
                print _("One of --serial or --all must be provided")
                self.parser.print_help()
                return
            self.certlib.update()
        except connection.RestlibException, re:
            log.error(re)
            systemExit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Unable to perform unsubscribe due to the following exception \n Error: %s") % e, e)
        #it is okay to call this no matter what happens above, it's just a notification to perform a check
        dbus_proxy_iface = self._get_dbus_iface()
        dbus_proxy_iface.check_compliance()


class FactsCommand(CliCommand):

    def __init__(self):
        usage = "usage: %prog facts [OPTIONS]"
        shortdesc = _("show information for facts")
        desc = "facts"
        CliCommand.__init__(self, "facts", usage, shortdesc, desc)

        self.parser.add_option("--list", action="store_true",
                               help=_("list known facts for this system"))
        self.parser.add_option("--update", action="store_true",
                               help=_("update the system facts"))

    def _validate_options(self):
        # Only require registration for updating facts
        if self.options.update:
            self.assert_should_be_registered()

        # one or the other
        if not (self.options.list or self.options.update):
            print _("Error: Need either --list or --update, Try facts --help")
            sys.exit(-1)

    def _do_command(self):
        self._validate_options()
        if self.options.list:
            facts = Facts()
            fact_dict = facts.get_facts()
            fact_keys = fact_dict.keys()
            fact_keys.sort()
            for key in fact_keys:
                print "%s: %s" % (key, fact_dict[key])

        if self.options.update:
            facts = Facts()
            consumer = check_registration()['uuid']
            print consumer
            self.cp.updateConsumerFacts(consumer, facts.get_facts())


class ListCommand(CliCommand):

    def __init__(self):
        usage = "usage: %prog list [OPTIONS]"
        shortdesc = _("list available or consumer subscriptions for registered user")
        desc = "list available or consumed Entitlement Pools for this system."
        CliCommand.__init__(self, "list", usage, shortdesc, desc)
        self.available = None
        self.consumed = None
        self.parser.add_option("--installed", action='store_true', help=_("installed"))
        self.parser.add_option("--available", action='store_true',
                               help=_("available"))
        self.parser.add_option("--ondate", dest="on_date",
                                help=_("date to search on, defaults to today's date, only used with --available "+
                                      "(example: ") + strftime("%Y-%m-%d", localtime()) + " )")
        self.parser.add_option("--consumed", action='store_true',
                               help=_("consumed"))
        self.parser.add_option("--all", action='store_true',
                               help=_("if supplied with --available then all subscriptions are returned"))

    def _validate_options(self):
        if (self.options.all and not self.options.available):
            print _("Error: --all is only applicable with --available")
            sys.exit(-1)
        if (self.options.on_date and not self.options.available):
            print _("Error: --ondate is only applicable with --available")
            sys.exit(-1)
        if not (self.options.available or self.options.consumed):
            self.options.installed = True

    def _do_command(self):
        """
        Executes the command.
        """

        self._validate_options()

        consumer = check_registration()['uuid']
        if self.options.installed:
            iproducts = managerlib.getInstalledProductStatus()
            if not len(iproducts):
                print(_("No installed Products to list"))
                sys.exit(0)
            print "+-------------------------------------------+"
            print _("    Installed Product Status")
            print "+-------------------------------------------+"
            for product in iproducts:
                print constants.installed_product_status % product

        if self.options.available:
            on_date = None
            if self.options.on_date:
                try:
                    # doing it this ugly way for pre python 2.5
                    on_date = datetime.datetime(
                            *(strptime(self.options.on_date, '%Y-%m-%d')[0:6]))
                except Exception, e:
                    print(_("Date entered is invalid. Date should be in YYYY-MM-DD format (example: ") + strftime("%Y-%m-%d", localtime()) + " )")
                    sys.exit(1)

            facts = Facts()
            epools = managerlib.getAvailableEntitlements(self.cp, consumer,
                    facts, self.options.all, on_date)
            if not len(epools):
                print(_("No Available subscription pools to list"))
                sys.exit(0)
            print "+-------------------------------------------+\n    %s\n+-------------------------------------------+\n" % _("Available Subscriptions")
            for data in epools:
                # TODO:  Something about these magic numbers!
                product_name = self._format_name(data['productName'], 24, 80)

                print constants.available_subs_list % (product_name,
                                                       data['productId'],
                                                       data['id'],
                                                       data['quantity'],
                                                       data['endDate'])

        if self.options.consumed:
            cpents = managerlib.getConsumedProductEntitlements()
            if not len(cpents):
                print(_("No Consumed subscription pools to list"))
                sys.exit(0)
            print """+-------------------------------------------+\n    %s\n+-------------------------------------------+\n""" % _("Consumed Product Subscriptions")
            for product in cpents:
                print constants.consumed_subs_list % product

    def _format_name(self, name, indent, max_length):
        """
        Formats a potentially long name for multi-line display, giving
        it a columned effect.
        """
        words = name.split()
        current = indent
        lines = []
        line = [words.pop(0)]

        def add_line():
            lines.append(' '.join(line))

        # Split here and build it back up by word, this way we get word wrapping
        for word in words:
            if current + len(word) < max_length:
                current += len(word) + 1  # Have to account for the extra space
                line.append(word)
            else:
                add_line()
                line = [' ' * (indent - 1), word]
                current = indent

        add_line()
        return '\n'.join(lines)


# taken wholseale from rho...
class CLI:

    def __init__(self):

        self.cli_commands = {}
        for clazz in [RegisterCommand, UnRegisterCommand, ListCommand, SubscribeCommand,\
                       UnSubscribeCommand, FactsCommand, IdentityCommand, \
                       RefreshCommand, CleanCommand, ActivateCommand]:
            cmd = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_commands[cmd.name] = cmd


    def _add_command(self, cmd):
        self.cli_commands[cmd.name] = cmd

    def _usage(self):
        print _("\nUsage: %s [options] MODULENAME --help\n") % os.path.basename(sys.argv[0])
        print _("Supported modules:")
        print "\n"

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
        i = len(possiblecmd)
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            cmd = self.cli_commands.get(key)
            i -= 1

        return cmd

    def main(self):
        managerlib.check_identity_cert_perms()

        cmd = self._find_best_match(sys.argv)
        if len(sys.argv) < 2 or not cmd:
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
    consumer_info = {"consumer_name": consumer.getConsumerName(),
                     "uuid": consumer.getConsumerId()}
    return consumer_info

if __name__ == "__main__":
    CLI().main()

