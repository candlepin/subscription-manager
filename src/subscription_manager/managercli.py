# -*- coding: utf-8 -*-
#
# Subscription manager command line utility.
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

import datetime
import dbus
import fnmatch
import getpass
import gettext
import logging
import os
import socket
import sys
from time import localtime, strftime, strptime
import unicodedata

from M2Crypto import SSL
from M2Crypto import X509

import rhsm.config
import rhsm.connection as connection

from subscription_manager.branding import get_branding
from subscription_manager.cache import InstalledProductsManager, ProfileManager
from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory
from subscription_manager.certlib import CertLib, ConsumerIdentity, Disconnected
from subscription_manager.certmgr import CertManager
from subscription_manager.cert_sorter import FUTURE_SUBSCRIBED, SUBSCRIBED, \
        NOT_SUBSCRIBED, EXPIRED, PARTIALLY_SUBSCRIBED, UNKNOWN
from subscription_manager.cli import AbstractCLICommand, CLI, system_exit
from subscription_manager.facts import Facts
from subscription_manager.hwprobe import ClassicCheck
import subscription_manager.injection as inj
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager import managerlib
from subscription_manager.managerlib import valid_quantity
from subscription_manager.release import ReleaseBackend
from subscription_manager.repolib import RepoFile, RepoLib
from subscription_manager.utils import remove_scheme, parse_server_info, \
        ServerUrlParseError, parse_baseurl_info, format_baseurl, is_valid_server_info, \
        MissingCaCertException, get_client_versions, get_server_versions, \
        restart_virt_who, get_terminal_width

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

cfg = rhsm.config.initConfig()


NOT_REGISTERED = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")
LIBRARY_ENV_NAME = "library"

# Translates the cert sorter status constants:
STATUS_MAP = {
        FUTURE_SUBSCRIBED: _("Future Subscription"),
        SUBSCRIBED: _("Subscribed"),
        NOT_SUBSCRIBED: _("Not Subscribed"),
        EXPIRED: _("Expired"),
        PARTIALLY_SUBSCRIBED: _("Partially Subscribed"),
        UNKNOWN: _("Unknown")
}

INSTALLED_PRODUCT_STATUS = [
    _("Product Name:"),
    _("Product ID:"),
    _("Version:"),
    _("Arch:"),
    _("Status:"),
    _("Status Details:"),
    _("Starts:"),
    _("Ends:")
]

AVAILABLE_SUBS_LIST = [
    _("Subscription Name:"),
    _("SKU:"),
    _("Pool ID:"),
    _("Quantity:"),
    _("Service Level:"),
    _("Service Type:"),
    _("Multi-Entitlement:"),
    _("Ends:"),
    _("System Type:")
]

REPOS_LIST = [
    _("Repo ID:"),
    _("Repo Name:"),
    _("Repo URL:"),
    _("Enabled:"),
]

PRODUCT_STATUS = [
    _("Product Name:"),
    _("Status:")
]

ENVIRONMENT_LIST = [
    _("Name:"),
    _("Description:")
]

ORG_LIST = [
    _("Name:"),
    _("Key:")
]

CONSUMED_LIST = [
    _("Subscription Name:"),
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Account:"),
    _("Serial:"),
    _("Pool ID:"),
    _("Active:"),
    _("Quantity Used:"),
    _("Service Level:"),
    _("Service Type:"),
    _("Status Details:"),
    _("Starts:"),
    _("Ends:")
]


def handle_exception(msg, ex):

    # On Python 2.4 and earlier, sys.exit triggers a SystemExit exception,
    # which can land us into this block of code. We do not want to handle
    # this or print any messages as the caller would already have done so,
    # so just re-throw and let Python have at it.
    if isinstance(ex, SystemExit):
        raise ex

    log.error(msg)
    log.exception(ex)
    if isinstance(ex, socket.error) or isinstance(ex, Disconnected):
        print _("Network error, unable to connect to server.")
        print _("Please see /var/log/rhsm/rhsm.log for more information.")
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
        print ex.msg
        sys.exit(-1)
    elif isinstance(ex, SSL.Checker.WrongHost):
        print str(ex)
        sys.exit(-1)
    elif isinstance(ex, connection.BadCertificateException):
        print _("Bad CA certificate: %s") % ex.cert_path
        sys.exit(-1)
    elif isinstance(ex, connection.ExpiredIdentityCertException):
        print _("Your identity certificate has expired")
        sys.exit(-1)
    else:
        system_exit(-1, ex)


def autosubscribe(cp, consumer_uuid, service_level=None):
    """
    This is a wrapper for bind/bindByProduct. Eventually, we will exclusively
    use bind, but for now, we support both.
    """
    if service_level:
        cp.updateConsumer(consumer_uuid, service_level=service_level)
        print(_("Service level set to: %s") % service_level)

    plugin_manager = inj.require(inj.PLUGIN_MANAGER)
    try:
        plugin_manager.run("pre_auto_attach", consumer_uuid=consumer_uuid)
        ents = cp.bind(consumer_uuid)  # new style
        plugin_manager.run("post_auto_attach", consumer_uuid=consumer_uuid, entitlement_data=ents)

    except Exception, e:
        log.warning("Error during auto-attach.")
        log.exception(e)


def show_autosubscribe_output(uep):
    installed_status = managerlib.get_installed_product_status(ProductDirectory(),
            EntitlementDirectory(), uep)
    if not installed_status:
        print _("No products installed.")
        return 1
    log.info("Attempted to auto-attach/heal the system.")
    print _("Installed Product Current Status:")
    subscribed = 1
    for prod_status in installed_status:
        if prod_status[4] == SUBSCRIBED:
            subscribed = 0
        status = STATUS_MAP[prod_status[4]]
        print columnize(PRODUCT_STATUS, _echo, prod_status[0], status) + "\n"
    return subscribed


class CliCommand(AbstractCLICommand):
    """ Base class for all sub-commands. """

    def __init__(self, name="cli", shortdesc=None, primary=False):
        AbstractCLICommand.__init__(self, name=name, shortdesc=shortdesc, primary=primary)

        self._add_common_options()

        self.server_url = None

        self.proxy_url = None
        self.proxy_hostname = None
        self.proxy_port = None

        self.entitlement_dir = inj.require(inj.ENT_DIR)
        self.product_dir = inj.require(inj.PROD_DIR)

        self.client_versions = self._default_client_version()
        self.server_versions = self._default_server_version()

        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)

    def _request_validity_check(self):
        try:
            bus = dbus.SystemBus()
            validity_obj = bus.get_object('com.redhat.SubscriptionManager',
                              '/EntitlementStatus')
            validity_iface = dbus.Interface(validity_obj,
                                dbus_interface='com.redhat.SubscriptionManager.EntitlementStatus')
        except dbus.DBusException:
            # we can't connect to dbus. it's not running, likely from a minimal
            # install. we can't do anything here, so just ignore it.
            return

        try:
            validity_iface.check_status()
        except dbus.DBusException:
            # the call timed out, or something similar. we don't really care
            # about a timely reply or what the result might be, we just want
            # the method to run. So we can safely ignore this.
            pass

    def _add_url_options(self):
        """ Add options that allow the setting of the server URL."""
        self.parser.add_option("--serverurl", dest="server_url",
                               default=None, help=_("server URL in the form of https://hostname:443/prefix"))
        self.parser.add_option("--insecure", action="store_true",
                                default=False, help=_("do not check the server SSL certificate against available certificate authorities"))

    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """
        self.parser.add_option("--proxy", dest="proxy_url",
                               default=None, help=_("proxy URL in the form of proxy_hostname:proxy_port"))
        self.parser.add_option("--proxyuser", dest="proxy_user",
                                default=None, help=_("user for HTTP proxy with basic authentication"))
        self.parser.add_option("--proxypassword", dest="proxy_password",
                                default=None, help=_("password for HTTP proxy with basic authentication"))

    def _do_command(self):
        pass

    def assert_should_be_registered(self):
        if not self.is_registered():
            print(NOT_REGISTERED)
            sys.exit(-1)

    def is_registered(self):
        return ConsumerIdentity.existsAndValid()

    def persist_server_options(self):
        """
        Whether to persist options like --serverurl or --baseurl to the
        rhsm.conf file when used.  For modules like register, we want this to
        be true.  For modules like orgs or environments, we want false.
        """
        return False

    def require_connection(self):
        return True

    def _default_client_version(self):
        return {"subscription-manager": _("Unknown"),
                "python-rhsm": _("Unknown")}

    def _default_server_version(self):
        return {"candlepin": _("Unknown"),
                "server-type": _("Unknown")}

    def log_client_version(self):
        self.client_versions = get_client_versions()
        log.info("Client Versions: %s" % self.client_versions)

    def log_server_version(self):
        # can't check the server version without a connection
        # and valid registration
        if not self.require_connection():
            return

        # get_server_versions needs to handle any exceptions
        # and return the server dict
        self.server_versions = get_server_versions(self.no_auth_cp)
        log.info("Server Versions: %s" % self.server_versions)

    def main(self, args=None):

        config_changed = False

        # In testing we sometimes specify args, otherwise use the default:
        if not args:
            args = sys.argv[1:]

        (self.options, self.args) = self.parser.parse_args(args)

        # we dont need argv[0] in this list...
        self.args = self.args[1:]
        # check for unparsed arguments
        if self.args:
            for arg in self.args:
                print _("cannot parse argument: %s") % arg
            sys.exit(-1)

        # set proxy before we try to connect to server
        self.proxy_hostname = remove_scheme(cfg.get('server', 'proxy_hostname'))
        self.proxy_port = cfg.get_int('server', 'proxy_port')
        self.proxy_user = cfg.get('server', 'proxy_user')
        self.proxy_password = cfg.get('server', 'proxy_password')

        self.server_hostname = cfg.get("server", "hostname")
        self.server_port = cfg.get("server", "port")
        self.server_prefix = cfg.get("server", "prefix")

        if hasattr(self.options, "insecure") and self.options.insecure:
            cfg.set("server", "insecure", "1")
            config_changed = True

        if hasattr(self.options, "server_url") and self.options.server_url:
            try:
                (self.server_hostname,
                 self.server_port,
                 self.server_prefix) = parse_server_info(self.options.server_url)
            except ServerUrlParseError, e:
                print _("Error parsing serverurl: %s") % e.msg
                sys.exit(-1)

            # this trys to actually connect to the server and ping it
            try:
                if not is_valid_server_info(self.server_hostname,
                                            self.server_port,
                                            self.server_prefix):
                    print _("Unable to reach the server at %s:%s%s") % \
                            (self.server_hostname,
                             self.server_port,
                             self.server_prefix)
                    sys.exit(-1)
            except MissingCaCertException:
                print _("Error: CA certificate for subscription service has not been installed.")
                sys.exit(-1)

            cfg.set("server", "hostname", self.server_hostname)
            cfg.set("server", "port", self.server_port)
            cfg.set("server", "prefix", self.server_prefix)

            config_changed = True

        if hasattr(self.options, "base_url") and self.options.base_url:
            try:
                (baseurl_server_hostname,
                 baseurl_server_port,
                 baseurl_server_prefix) = parse_baseurl_info(self.options.base_url)
            except ServerUrlParseError, e:
                print _("Error parsing baseurl: %s") % e.msg
                sys.exit(-1)

            cfg.set("rhsm", "baseurl", format_baseurl(baseurl_server_hostname,
                                                      baseurl_server_port,
                                                      baseurl_server_prefix))
            config_changed = True

        # support foo.example.com:3128 format
        if hasattr(self.options, "proxy_url") and self.options.proxy_url:
            parts = remove_scheme(self.options.proxy_url).split(':')
            self.proxy_hostname = parts[0]
            # no ':'
            if len(parts) > 1:
                self.proxy_port = int(parts[1])
            else:
                # if no port specified, use the one from the config, or fallback to the default
                self.proxy_port = cfg.get_int('server', 'proxy_port') or rhsm.config.DEFAULT_PROXY_PORT

        if hasattr(self.options, "proxy_user") and self.options.proxy_user:
            self.proxy_user = self.options.proxy_user
        if hasattr(self.options, "proxy_password") and self.options.proxy_password:
            self.proxy_password = self.options.proxy_password

        # Proxy information isn't written to the config, so we have to make sure
        # the sorter gets it
        connection_info = {}
        if self.proxy_hostname:
            connection_info['proxy_hostname_arg'] = self.proxy_hostname
        if self.proxy_port:
            connection_info['proxy_port_arg'] = self.proxy_port
        if self.proxy_user:
            connection_info['proxy_user_arg'] = self.proxy_user
        if self.proxy_password:
            connection_info['proxy_password_arg'] = self.proxy_password
        if self.server_hostname:
            connection_info['host'] = self.server_hostname
        if self.server_port:
            connection_info['ssl_port'] = self.server_port
        if self.server_prefix:
            connection_info['handler'] = self.server_prefix

        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.cp_provider.set_connection_info(**connection_info)

        self.log_client_version()

        if self.require_connection():
            # make sure we pass in the new server info, otherwise we
            # we use the defaults from connection module init
            # we've set self.proxy* here, so we'll use them if they
            # are set
            self.cp = self.cp_provider.get_consumer_auth_cp()

            # no auth cp for get / (resources) and
            # get /status (status and versions)
            self.no_auth_cp = self.cp_provider.get_no_auth_cp()
            self.log_server_version()

            self.certlib = CertLib(uep=self.cp)

        else:
            self.cp = None

        # do the work, catch most common errors here:
        try:
            return_code = self._do_command()

            # Only persist the config changes if there was no exception
            if config_changed and self.persist_server_options():
                cfg.save()

            if return_code is not None:
                return return_code
        except X509.X509Error, e:
            log.error(e)
            print _('System certificates corrupted. Please reregister.')


class UserPassCommand(CliCommand):

    """
    Abstract class for commands that require a username and password
    """

    def __init__(self, name, shortdesc=None, primary=False):
        super(UserPassCommand, self).__init__(name, shortdesc, primary)
        self._username = None
        self._password = None

        self.parser.add_option("--username", dest="username",
                               help=_("username to use when authorizing against the server"))
        self.parser.add_option("--password", dest="password",
                               help=_("password to use when authorizing against the server"))

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


class OrgCommand(UserPassCommand):
    """
    Abstract class for commands that require an org.
    """
    def __init__(self, name, shortdesc=None, primary=False):
        super(OrgCommand, self).__init__(name, shortdesc, primary)
        self._org = None
        if not hasattr(self, "_org_help_text"):
            self._org_help_text = _("specify organization")
        self.parser.add_option("--org", dest="org", metavar="ORG_KEY",
            help=self._org_help_text)

    @staticmethod
    def _get_org(org):
        if not org:
            while not org:
                org = raw_input(_("Organization: "))
        return org

    @property
    def org(self):
        if not self._org:
            self._org = self._get_org(self.options.org)
        return self._org


class CleanCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Remove all local system and subscription data without affecting the server")

        super(CleanCommand, self).__init__("clean", shortdesc, False)

    def _add_common_options(self):
        # remove these options as per bz #664581
        return

    def _do_command(self):
        managerlib.clean_all_data(False)
        print (_("All local data removed"))

        self._request_validity_check()

        # We have new credentials, restart virt-who
        restart_virt_who()

    def require_connection(self):
        return False


class RefreshCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Pull the latest subscription data from the server")

        super(RefreshCommand, self).__init__("refresh", shortdesc, True)

    def _do_command(self):
        check_registration()
        try:
            self.certlib.update()
            log.info("Refreshed local data")
            print (_("All local data refreshed"))
        except connection.RestlibException, re:
            log.error(re)
            system_exit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Unable to perform refresh due to the following exception: %s") % e, e)

        self._request_validity_check()


class IdentityCommand(UserPassCommand):
    def __init__(self):
        shortdesc = _("Display the identity certificate for this system or "
                      "request a new one")

        super(IdentityCommand, self).__init__("identity", shortdesc, False)

        self.parser.add_option("--regenerate", action='store_true',
                               help=_("request a new certificate be generated"))
        self.parser.add_option("--force", action='store_true',
                               help=_("force certificate regeneration (requires username and password)"))

    def _validate_options(self):
        self.assert_should_be_registered()
        if self.options.force and not self.options.regenerate:
            print(_("--force can only be used with --regenerate"))
            sys.exit(-1)
        if (self.options.username or self.options.password) and \
                not self.options.force:
            print(_("--username and --password can only be used with --force"))
            sys.exit(-1)

    def _do_command(self):
        # check for Classic before doing anything else
        if ClassicCheck().is_registered_with_classic():
            if ConsumerIdentity.existsAndValid():
                print _("server type: %s") % get_branding().REGISTERED_TO_BOTH_SUMMARY
            else:
                # no need to continue if user is only registered to Classic
                print _("server type: %s") % get_branding().REGISTERED_TO_OTHER_SUMMARY
                return

        try:
            consumer = check_registration()
            self._validate_options()
            consumerid = consumer['uuid']
            consumer_name = consumer['consumer_name']
            if not self.options.regenerate:
                owner = self.cp.getOwner(consumerid)
                ownername = owner['displayName']
                ownerid = owner['key']

                print _('Current identity is: %s') % consumerid
                print _('name: %s') % consumer_name
                print _('org name: %s') % ownername
                print _('org ID: %s') % ownerid

                if self.cp.supports_resource('environments'):
                    consumer = self.cp.getConsumer(consumerid)
                    environment = consumer['environment']
                    if environment:
                        environment_name = environment['name']
                    else:
                        environment_name = _("None")
                    print _('environment name: %s') % environment_name
            else:
                if self.options.force:
                    # get an UEP with basic auth
                    self.cp_provider.set_user_pass(self.username, self.password)
                    self.cp = self.cp_provider.get_basic_auth_cp()
                consumer = self.cp.regenIdCertificate(consumerid)
                managerlib.persist_consumer_cert(consumer)
                print _("Identity certificate has been regenerated.")

                log.info("Successfully generated a new identity from server.")
        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to generate a new identity for the system: %s" % re)
            system_exit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to generate a new identity for the system"), e)


class OwnersCommand(UserPassCommand):

    def __init__(self):
        shortdesc = _("Display the organizations against which a user can register a system")

        super(OwnersCommand, self).__init__("orgs", shortdesc, False)

        self._add_url_options()

    def _do_command(self):

        try:
            # get a UEP
            self.cp_provider.set_user_pass(self.username, self.password)
            self.cp = self.cp_provider.get_basic_auth_cp()
            owners = self.cp.getOwnerList(self.username)
            log.info("Successfully retrieved org list from server.")
            if len(owners):
                print("+-------------------------------------------+")
                print("          %s %s" % (self.username, _("Organizations")))
                print("+-------------------------------------------+")
                print("")
                for owner in owners:
                    print columnize(ORG_LIST, _echo,
                            owner['displayName'], owner['key']) + "\n"
            else:
                print(_("%s cannot register with any organizations.") % self.username)

        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to retrieve org list from server: %s" % re)
            system_exit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to retrieve org list from server"), e)


class EnvironmentsCommand(OrgCommand):

    def __init__(self):
        shortdesc = _("Display the environments available for a user")
        self._org_help_text = \
            _("specify organization for environment list, using organization key")

        super(EnvironmentsCommand, self).__init__("environments", shortdesc,
                                                  False)
        self._add_url_options()

    def _get_enviornments(self, org):
        raw_environments = self.cp.getEnvironmentList(org)
        environments = []
        # Remove the library environemnt
        for env in raw_environments:
            if env['name'].lower() != LIBRARY_ENV_NAME.lower():
                environments.append(env)
        return environments

    def _do_command(self):
        self._validate_options()
        try:
            self.cp_provider.set_user_pass(self.username, self.password)
            self.cp = self.cp_provider.get_basic_auth_cp()
            if self.cp.supports_resource('environments'):
                environments = self._get_enviornments(self.org)

                if len(environments):
                    print("+-------------------------------------------+")
                    print("          %s" % (_("Environments")))
                    print("+-------------------------------------------+")
                    for env in environments:
                        print columnize(ENVIRONMENT_LIST, _echo, env['name'],
                                env['description']) + "\n"
                else:
                    print _("Error: This org does not have environments.")
            else:
                print _("Error: Server does not support environments.")

            log.info("Successfully retrieved environment list from server.")
        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to retrieve environment list from server: %s" % re)
            system_exit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to retrieve environment list from server"), e)


class ServiceLevelCommand(OrgCommand):

    def __init__(self):
        self.consumerIdentity = ConsumerIdentity

        shortdesc = _("Manage service levels for this system")
        self._org_help_text = \
            _("specify an organization when listing available service levels using the organization key")
        super(ServiceLevelCommand, self).__init__("service-level", shortdesc,
                                                  False)

        self._add_url_options()
        self.parser.add_option("--show", dest="show", action='store_true',
                help=_("show this system's current service level"))
        self.parser.add_option("--list", dest="list", action='store_true',
                help=_("list all service levels available"))
        self.parser.add_option("--set", dest="service_level",
                               help=_("service level to apply to this system"))
        self.parser.add_option("--unset", dest="unset",
                               action='store_true',
                               help=_("unset the service level for this system"))

    def _set_service_level(self, service_level):
        consumer_uuid = self.consumerIdentity.read().getConsumerId()
        consumer = self.cp.getConsumer(consumer_uuid)
        if 'serviceLevel' not in consumer:
            system_exit(-1, _("Error: The service-level command is not supported "
                             "by the server."))
        self.cp.updateConsumer(consumer_uuid, service_level=service_level)

    def _validate_options(self):

        if self.options.service_level:
            self.options.service_level = self.options.service_level.strip()

        # Assume --show if run with no args:
        if not self.options.list and \
           not self.options.show and \
           not self.options.service_level and \
           not self.options.service_level == "" and \
           not self.options.unset:
            self.options.show = True

        if self.options.org and \
           not self.options.list:
            print(_("Error: --org is only supported with the --list option"))
            sys.exit(-1)

        if not self.consumerIdentity.existsAndValid():
            if self.options.list:
                if not (self.options.username and self.options.password):
                    print(_("Error: you must register or specify --username and --password to list service levels"))
                    sys.exit(-1)
            else:
                print(NOT_REGISTERED)
                sys.exit(-1)

    def _do_command(self):
        self._validate_options()
        try:
            # If we have a username/password, we're going to use that, otherwise
            # we'll use the identity certificate. We already know one or the other
            # exists:
            if self.options.username and self.options.password:
                self.cp_provider.set_user_pass(self.username, self.password)
                self.cp = self.cp_provider.get_basic_auth_cp()
            else:
                # get an UEP as consumer
                self.cp = self.cp_provider.get_consumer_auth_cp()

            if self.options.unset:
                self.unset_service_level()

            if self.options.service_level is not None:
                self.set_service_level(self.options.service_level)

            if self.options.show:
                self.show_service_level()

            if self.options.list:
                self.list_service_levels()

        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to retrieve service levels: %s" % re)
            system_exit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to retrieve service levels."), e)

    def set_service_level(self, service_level):
        if service_level == "":
            self.unset_service_level()
        else:
            self._set_service_level(service_level)
            print(_("Service level set to: %s") % service_level)

    def unset_service_level(self):
        self._set_service_level("")
        print _("Service level preference has been unset")

    def show_service_level(self):
        consumer_uuid = self.consumerIdentity.read().getConsumerId()
        consumer = self.cp.getConsumer(consumer_uuid)
        if 'serviceLevel' not in consumer:
            system_exit(-1, _("Error: The service-level command is not supported by "
                             "the server."))
        service_level = consumer['serviceLevel'] or ""
        if service_level:
            print(_("Current service level: %s") % service_level)
        else:
            print _("Service level preference not set")

    def list_service_levels(self):
        not_supported = _("Error: The service-level command is not supported by "
                          "the server.")

        org_key = self.options.org
        if not org_key:
            if self.consumerIdentity.existsAndValid():
                consumer_uuid = self.consumerIdentity.read().getConsumerId()
                org_key = self.cp.getOwner(consumer_uuid)['key']
            else:
                org_key = self.org

        try:
            slas = self.cp.getServiceLevelList(org_key)
            if len(slas):
                print("+-------------------------------------------+")
                print("               %s" % (_("Available Service Levels")))
                print("+-------------------------------------------+")
                for sla in slas:
                    print sla
            else:
                print _("This org does not have any subscriptions with service levels.")
        except connection.RemoteServerException, e:
            system_exit(-1, not_supported)
        except connection.RestlibException, e:
            if e.code == 404 and\
                e.msg.find('/servicelevels') > 0:
                system_exit(-1, not_supported)
            else:
                raise e


class RegisterCommand(UserPassCommand):
    def __init__(self):
        shortdesc = get_branding().CLI_REGISTER
        self.consumerIdentity = ConsumerIdentity

        super(RegisterCommand, self).__init__("register", shortdesc, True)

        self._add_url_options()
        self.parser.add_option("--baseurl", dest="base_url",
                              default=None, help=_("base URL for content in form of https://hostname:443/prefix"))
        self.parser.add_option("--type", dest="consumertype", default="system", metavar="UNITTYPE",
                               help=_("the type of unit to register, defaults to system"))
        self.parser.add_option("--name", dest="consumername", metavar="SYSTEMNAME",
                               help=_("name of the system to register, defaults to the hostname"))
        self.parser.add_option("--consumerid", dest="consumerid", metavar="SYSTEMID",
                               help=_("the existing system data is pulled from the server"))
        self.parser.add_option("--org", dest="org", metavar="ORG_KEY",
                               help=_("register with one of multiple organizations for the user, using organization key"))
        self.parser.add_option("--environment", dest="environment",
                               help=_("register with a specific environment in the destination org"))
        self.parser.add_option("--release", dest="release",
                               help=_("set a release version"))
        self.parser.add_option("--autosubscribe", action='store_true',
                               help=_("Deprecated, see --auto-attach"))
        self.parser.add_option("--auto-attach", action='store_true', dest="autoattach",
                               help=_("automatically attach compatible subscriptions to this system"))
        self.parser.add_option("--force", action='store_true',
                               help=_("register the system even if it is already registered"))
        self.parser.add_option("--activationkey", action='append', dest="activation_keys",
                               help=_("activation key to use for registration (can be specified more than once)"))
        self.parser.add_option("--servicelevel", dest="service_level",
                               help=_("system preference used when subscribing automatically"))

        self.facts = Facts(ent_dir=self.entitlement_dir,
                           prod_dir=self.product_dir)

    def _validate_options(self):
        self.autoattach = self.options.autosubscribe or self.options.autoattach
        if self.consumerIdentity.exists() and not self.options.force:
            print(_("This system is already registered. Use --force to override"))
            sys.exit(1)
        elif (self.options.consumername == ''):
            print(_("Error: system name can not be empty."))
            sys.exit(-1)
        elif (self.options.username and self.options.activation_keys):
            print(_("Error: Activation keys do not require user credentials."))
            sys.exit(-1)
        elif (self.options.consumerid and self.options.activation_keys):
            print(_("Error: Activation keys can not be used with previously registered IDs."))
            sys.exit(-1)
        elif (self.options.environment and self.options.activation_keys):
            print(_("Error: Activation keys do not allow environments to be specified."))
            sys.exit(-1)
        elif (self.autoattach and self.options.activation_keys):
            print(_("Error: Activation keys cannot be used with --auto-attach."))
            sys.exit(-1)
        #746259: Don't allow the user to pass in an empty string as an activation key
        elif (self.options.activation_keys and '' in self.options.activation_keys):
            print(_("Error: Must specify an activation key"))
            sys.exit(-1)
        elif (self.options.service_level and not self.autoattach):
            print(_("Error: Must use --auto-attach with --servicelevel."))
            sys.exit(-1)
        elif (self.options.activation_keys and not self.options.org):
            print(_("Error: Must provide --org with activation keys."))
            sys.exit(-1)

    def persist_server_options(self):
        """
        If the user provides a --serverurl or --baseurl, we want to persist it
        to the config file so that future commands will use the value.
        """
        return True

    def _do_command(self):
        """
        Executes the command.
        """

        self.log_client_version()

        # Always warn the user if registered to old RHN/Spacewalk
        if ClassicCheck().is_registered_with_classic():
            print(get_branding().REGISTERED_TO_OTHER_WARNING)

        self._validate_options()

        # gather installed products info
        self.installed_mgr = InstalledProductsManager()

        # Set consumer's name to hostname by default:
        consumername = self.options.consumername
        if consumername is None:
            consumername = socket.gethostname()

        if ConsumerIdentity.exists() and self.options.force:
            # First let's try to un-register previous consumer. This may fail
            # if consumer has already been deleted so we will continue even if
            # errors are encountered.
            if ConsumerIdentity.existsAndValid():
                old_uuid = ConsumerIdentity.read().getConsumerId()
                try:
                    managerlib.unregister(self.cp, old_uuid)
                    log.info("--force specified, unregistered old consumer: %s" % old_uuid)
                    print(_("The system with UUID %s has been unregistered") % old_uuid)
                except Exception, e:
                    log.error("Unable to unregister consumer: %s" % old_uuid)
                    log.exception(e)

        # Proceed with new registration:
        try:
            if not self.options.activation_keys:
                self.cp_provider.set_user_pass(self.username, self.password)
                admin_cp = self.cp_provider.get_basic_auth_cp()
            else:
                admin_cp = self.cp_provider.get_no_auth_cp()

            facts_dic = self.facts.get_facts()

            self.plugin_manager.run("pre_register_consumer", name=consumername,
                                    facts=facts_dic)

            if self.options.consumerid:
                #TODO remove the username/password
                log.info("Registering as existing consumer: %s" %
                        self.options.consumerid)
                consumer = admin_cp.getConsumer(self.options.consumerid,
                        self.username, self.password)
            else:
                owner_key = self._determine_owner_key(admin_cp)

                environment_id = self._get_environment_id(admin_cp, owner_key,
                        self.options.environment)

                consumer = admin_cp.registerConsumer(name=consumername,
                     type=self.options.consumertype, facts=facts_dic,
                     owner=owner_key, environment=environment_id,
                     keys=self.options.activation_keys,
                     installed_products=self.installed_mgr.format_for_server())
                self.installed_mgr.write_cache()
            self.plugin_manager.run("post_register_consumer", consumer=consumer,
                                    facts=facts_dic)
        except connection.RestlibException, re:
            log.exception(re)
            system_exit(-1, re.msg)
        except Exception, e:
            handle_exception(_("Error during registration: %s") % e, e)

        consumer_info = self._persist_identity_cert(consumer)

        # We have new credentials, restart virt-who
        restart_virt_who()

        print (_("The system has been registered with ID: %s ")) % (consumer_info["uuid"])

        # get a new UEP as the consumer
        self.cp = self.cp_provider.get_consumer_auth_cp()

        # Reload the consumer identity:
        self.identity = inj.FEATURES.require(inj.IDENTITY)
        self.identity.reload()

        # log the version of the server we registered to
        self.log_server_version()

        # Must update facts to clear out the old ones:
        if self.options.consumerid:
            log.info("Updating facts")
            self.facts.update_check(self.cp, consumer['uuid'], force=True)

        profile_mgr = ProfileManager()
        # 767265: always force an upload of the packages when registering
        profile_mgr.update_check(self.cp, consumer['uuid'], True)

        # Facts and installed products went out with the registration request,
        # manually write caches to disk:
        self.facts.write_cache()
        self.installed_mgr.update_check(self.cp, consumer['uuid'])

        if self.options.release:
            # TODO: grab the list of valid options, and check
            self.cp.updateConsumer(consumer['uuid'], release=self.options.release)

        if self.autoattach:
            if 'serviceLevel' not in consumer and self.options.service_level:
                system_exit(-1, _("Error: The --servicelevel option is not supported "
                                 "by the server. Did not complete your request."))
            autosubscribe(self.cp, consumer['uuid'],
                    service_level=self.options.service_level)
        if (self.options.consumerid or self.options.activation_keys or
                self.autoattach):
            self.certlib.update()

        # run this after certlib update, so we have the new entitlements
        subscribed = 0
        if self.autoattach:
            subscribed = show_autosubscribe_output(self.cp)
        self._request_validity_check()
        return subscribed

    def _persist_identity_cert(self, consumer):
        """
        Parses the consumer dict returned from the cert, pulls out the identity
        certificate, and writes to disk.
        """
        return managerlib.persist_consumer_cert(consumer)

    def _get_environment_id(self, cp, owner_key, environment_name):
        # If none specified on CLI, return None, the registration method
        # will skip environment specification.
        if not environment_name:
            return environment_name

        if not cp.supports_resource('environments'):
            system_exit(-1, _("Error: Server does not support environments."))

        env = cp.getEnvironment(owner_key=owner_key, name=environment_name)
        if not env:
            system_exit(-1, _("No such environment: %s") % environment_name)
        return env['id']

    def _determine_owner_key(self, cp):
        """
        If given an owner in the options, use it. Otherwise ask the server
        for all the owners this user has access too. If there is just one,
        use its key. If multiple, ask the user.
        """
        if self.options.org:
            return self.options.org

        owners = cp.getOwnerList(self.username)

        if len(owners) == 0:
            system_exit(-1, _("%s cannot register with any organizations.") % self.username)
        if len(owners) == 1:
            return owners[0]['key']

        owner_key = None
        while not owner_key:
            owner_key = raw_input(_("Organization: "))
        return owner_key


class UnRegisterCommand(CliCommand):

    def __init__(self):
        shortdesc = get_branding().CLI_UNREGISTER

        super(UnRegisterCommand, self).__init__("unregister", shortdesc,
                                                True)

    def _validate_options(self):
        pass

    def _do_command(self):
        if not ConsumerIdentity.exists():
            print(_("This system is currently not registered."))
            sys.exit(1)

        try:
            consumer = check_registration()['uuid']
            managerlib.unregister(self.cp, consumer)
        except Exception, e:
            handle_exception("Unregister failed", e)

        #this block is simply to ensure that the yum repos got updated. If it fails,
        #there is no issue since it will most likely be cleaned up elsewhere (most
        #likely by the yum plugin)
        try:
            # there is no consumer cert at this point, a uep object
            # is not useful
            certmgr = CertManager(uep=None)
            certmgr.update()
        except Exception, e:
            pass

        self._request_validity_check()

        # We have new credentials, restart virt-who
        restart_virt_who()

        print(_("System has been unregistered."))


class RedeemCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Attempt to redeem a subscription for a preconfigured system")
        super(RedeemCommand, self).__init__("redeem", shortdesc, False)

        self.parser.add_option("--email", dest="email", action='store',
                               help=_("email address to notify when "
                               "subscription redemption is complete"))
        self.parser.add_option("--locale", dest="locale", action='store',
                               help=_("optional language to use for email "
                               "notification when subscription redemption is "
                               "complete (Examples: en-us, de-de)"))

    def _validate_options(self):
        if not self.options.email:
            print(_("Error: This command requires that you specify an email address with --email."))
            sys.exit(-1)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer_uuid = check_registration()['uuid']
        self._validate_options()

        try:
            # update facts first, if we need to
            facts = Facts(ent_dir=self.entitlement_dir,
                          prod_dir=self.product_dir)
            facts.update_check(self.cp, consumer_uuid)

            profile_mgr = ProfileManager()
            profile_mgr.update_check(self.cp, consumer_uuid)

            self.cp.activateMachine(consumer_uuid, self.options.email, self.options.locale)

        except connection.RestlibException, e:
            #candlepin throws an exception during activateMachine, even for
            #200's. We need to look at the code in the RestlibException and proceed
            #accordingly
            if 200 <= e.code <= 210:
                system_exit(0, e)
            else:
                handle_exception(u"Unable to redeem: %s" % e, e)
        except Exception, e:
            handle_exception(u"Unable to redeem: %s" % e, e)

        self._request_validity_check()


class ReleaseCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Configure which operating system release to use")
        super(ReleaseCommand, self).__init__("release", shortdesc, True)

        self.parser.add_option("--show", dest="show", action="store_true",
                               help=_("shows current release setting; default command"))
        self.parser.add_option("--list", dest="list", action="store_true",
                               help=_("list available releases"))
        self.parser.add_option("--set", dest="release", action="store",
                               default=None,
                               help=_("set the release for this system"))
        self.parser.add_option("--unset", dest="unset",
                               action='store_true',
                               help=_("unset the release for this system"))

    def _get_consumer_release(self):
        err_msg = _("Error: The 'release' command is not supported by the server.")
        consumer = self.cp.getConsumer(self.consumer['uuid'])
        if 'releaseVer' not in consumer:
            system_exit(-1, err_msg)
        return consumer['releaseVer']['releaseVer']

    def show_current_release(self):
        release = self._get_consumer_release()
        if release:
            print _("Release: %s") % release
        else:
            print _("Release not set")

    def _do_command(self):
        cdn_url = cfg.get('rhsm', 'baseurl')
        # note: parse_baseurl_info will populate with defaults if not found
        (cdn_hostname, cdn_port, cdn_prefix) = parse_baseurl_info(cdn_url)

        self.cc = connection.ContentConnection(host=cdn_hostname,
                                               ssl_port=cdn_port,
                                               proxy_hostname=self.proxy_hostname,
                                               proxy_port=self.proxy_port,
                                               proxy_user=self.proxy_user,
                                               proxy_password=self.proxy_password)

        self.release_backend = ReleaseBackend(ent_dir=self.entitlement_dir,
                                              prod_dir=self.product_dir,
                                              content_connection=self.cc,
                                              uep=self.cp)

        self.consumer = check_registration()
        if self.options.unset:
            self.cp.updateConsumer(self.consumer['uuid'],
                        release="")
            print _("Release preference has been unset")
        elif self.options.release is not None:
            # check first if the server supports releases
            self._get_consumer_release()
            releases = self.release_backend.get_releases()
            if self.options.release in releases:
                self.cp.updateConsumer(self.consumer['uuid'],
                        release=self.options.release)
            else:
                system_exit(-1, _("No releases match '%s'.  "
                                 "Consult 'release --list' for a full listing.")
                                 % self.options.release)
            print _("Release set to: %s") % self.options.release
        elif self.options.list:
            self._get_consumer_release()
            releases = self.release_backend.get_releases()
            if not releases:
                system_exit(-1, _("No release versions available, please check subscriptions."))

            print("+-------------------------------------------+")
            print("          %s" % (_("Available Releases")))
            print("+-------------------------------------------+")
            for release in releases:
                print release

        else:
            self.show_current_release()


class AttachCommand(CliCommand):

    def __init__(self):
        super(AttachCommand, self).__init__(
            self._command_name(),
            self._short_description(),
            self._primary())

        self.product = None
        self.substoken = None
        self.parser.add_option("--pool", dest="pool", action='append',
                               help=_("the ID of the pool to attach (can be specified more than once)"))
        self.parser.add_option("--quantity", dest="quantity",
                               help=_("number of subscriptions to attach"))
        self.parser.add_option("--auto", action='store_true',
            help=_("automatically attach compatible subscriptions to this system"))
        self.parser.add_option("--servicelevel", dest="service_level",
                               help=_("service level to apply to this system"))
        # re bz #864207
        _("All installed products are covered by valid entitlements.")
        _("No need to update subscriptions at this time.")

    def _short_description(self):
        return _("Attach a specified subscription to the registered system")

    def _command_name(self):
        return "attach"

    def _primary(self):
        return True

    def _validate_options(self):
        if not (self.options.pool or self.options.auto):
            print _("Error: This command requires that you specify a pool with --pool or use --auto.")
            sys.exit(-1)
        if self.options.pool and self.options.auto:
            print _("Error: Only one of --pool or --auto may be used with this command.")
            sys.exit(-1)

        # Quantity must be a positive integer
        quantity = self.options.quantity
        if self.options.quantity:
            if not valid_quantity(quantity):
                print _("Error: Quantity must be a positive integer.")
                sys.exit(-1)
            else:
                self.options.quantity = int(self.options.quantity)

        if (self.options.service_level and not self.options.auto):
            print(_("Error: Must use --auto with --servicelevel."))
            sys.exit(-1)

    def _do_command(self):
        """
        Executes the command.
        """
        consumer_uuid = check_registration()['uuid']
        self._validate_options()
        try:
            certmgr = CertManager(uep=self.cp)
            certmgr.update()
            return_code = 0
            cert_update = True
            if self.options.pool:
                subscribed = False
                for pool in self.options.pool:
                    try:
                        # odd html strings will cause issues, reject them here.
                        if (pool.find("#") >= 0):
                            system_exit(-1, _("Please enter a valid numeric pool ID."))
                        # If quantity is None, server will assume 1. pre_subscribe will
                        # report the same.
                        self.plugin_manager.run("pre_subscribe",
                                                consumer_uuid=consumer_uuid,
                                                pool_id=pool,
                                                quantity=self.options.quantity or 1)
                        ents = self.cp.bindByEntitlementPool(consumer_uuid, pool, self.options.quantity)
                        self.plugin_manager.run("post_subscribe", consumer_uuid=consumer_uuid, entitlement_data=ents)
                        # Usually just one, but may as well be safe:
                        for ent in ents:
                            pool_json = ent['pool']
                            print _("Successfully attached a subscription for: %s") % pool_json['productName']
                            log.info("Successfully attached a subscription for: %s (%s)" %
                                    (pool_json['productName'], pool))
                            subscribed = True
                    except connection.RestlibException, re:
                        log.exception(re)
                        if re.code == 403:
                            print re.msg  # already subscribed.
                        elif re.code == 400:
                            print re.msg  # no such pool.
                        else:
                            system_exit(-1, re.msg)  # some other error.. don't try again
                if not subscribed:
                    return_code = 1
            # must be auto
            else:
                products_installed = len(managerlib.get_installed_product_status(self.product_dir,
                                 self.entitlement_dir, self.cp))
                # if we are green, we don't need to go to the server
                self.sorter = inj.require(inj.CERT_SORTER)

                if self.sorter.is_valid():
                    if not products_installed:
                        print _("No Installed products on system. "
                                "No need to attach subscriptions.")
                    else:
                        print _("All installed products are covered by valid entitlements. "
                                "No need to update subscriptions at this time.")
                    cert_update = False
                else:
                    # If service level specified, make an additional request to
                    # verify service levels are supported on the server:
                    if self.options.service_level:
                        consumer = self.cp.getConsumer(consumer_uuid)
                        if 'serviceLevel' not in consumer:
                            system_exit(-1, _("Error: The --servicelevel option is not "
                                             "supported by the server. Did not "
                                             "complete your request."))
                    autosubscribe(self.cp, consumer_uuid,
                                  service_level=self.options.service_level)
            result = None
            if cert_update:
                result = self.certlib.update()

            if result and result[1]:
                print 'Entitlement Certificate(s) update failed due to the following reasons:'
                for e in result[1]:
                    print '\t-', str(e)
            elif self.options.auto:
                if not products_installed:
                    return_code = 1
                else:
                    # run this after certlib update, so we have the new entitlements
                    return_code = show_autosubscribe_output(self.cp)

        except Exception, e:
            handle_exception("Unable to attach: %s" % e, e)

        # it is okay to call this no matter what happens above,
        # it's just a notification to perform a check
        self._request_validity_check()
        return return_code


class SubscribeCommand(AttachCommand):
    def __init__(self):
        super(SubscribeCommand, self).__init__()

    def _short_description(self):
        return _("Deprecated, see attach")

    def _command_name(self):
        return "subscribe"

    def _primary(self):
        return False


class RemoveCommand(CliCommand):

    def __init__(self):
        super(RemoveCommand, self).__init__(
            self._command_name(),
            self._short_description(),
            self._primary())

        self.parser.add_option("--serial", action='append', dest="serials", metavar="SERIAL",
                       help=_("certificate serial number to remove (can be specified more than once)"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("remove all subscriptions from this system"))

    def _short_description(self):
        return _("Remove all or specific subscriptions from this system")

    def _command_name(self):
        return "remove"

    def _primary(self):
        return True

    def _validate_options(self):
        if self.options.serials:
            bad = False
            for serial in self.options.serials:
                if not serial.isdigit():
                    print _("Error: '%s' is not a valid serial number") % serial
                    bad = True
            if bad:
                system_exit(-1)
        elif not self.options.all:
            print _("Error: This command requires that you specify one of --serial or --all.")
            system_exit(-1)

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        return_code = 0
        if ConsumerIdentity.exists():
            consumer = ConsumerIdentity.read().getConsumerId()
            try:
                if self.options.all:
                    total = self.cp.unbindAll(consumer)
                    # total will be None on older Candlepins that don't
                    # support returning the number of subscriptions unsubscribed from
                    if total is None:
                        print _("All subscriptions have been removed at the server.")
                    else:
                        count = total['deletedRecords']
                        print gettext.ngettext("%s subscription removed at the server.",
                                               "%s subscriptions removed at the server.",
                                                count) % count
                else:
                    success = []
                    failure = []
                    for serial in self.options.serials:
                        try:
                            self.cp.unbindBySerial(consumer, serial)
                            success.append(serial)
                        except connection.RestlibException, re:
                            if re.code == 410:
                                print re.msg
                                system_exit(-1)
                            failure.append(re.msg)
                    if success:
                        print _("Serial numbers successfully removed at the server:")
                        for ser in success:
                            print "   %s" % ser
                    if failure:
                        print _("Serial numbers unsuccessfully removed at the server:")
                        for fail in failure:
                            print "   %s" % fail
                    if not success:
                        return_code = 1
                self.certlib.update()
            except connection.RestlibException, re:
                log.error(re)
                system_exit(-1, re.msg)
            except Exception, e:
                handle_exception(_("Unable to perform remove due to the following exception: %s") % e, e)
        else:
            # We never got registered, just remove the cert
            try:
                if self.options.all:
                    total = 0
                    for ent in self.entitlement_dir.list():
                        ent.delete()
                        total = total + 1
                    print (_("%s subscriptions removed from this system.") % total)
                else:
                    count = 0
                    for ent in self.entitlement_dir.list():
                        if str(ent.serial) in self.options.serials:
                            ent.delete()
                            print _("Subscription with serial number %s removed from this system") \
                                    % str(ent.serial)
                            count = count + 1
                    if count == 0:
                        return_code = 1
            except Exception, e:
                handle_exception(_("Unable to perform remove due to the following exception: %s") % e, e)

        # it is okay to call this no matter what happens above,
        # it's just a notification to perform a check
        self._request_validity_check()
        return return_code


class UnSubscribeCommand(RemoveCommand):
    def __init__(self):
        super(UnSubscribeCommand, self).__init__()

    def _short_description(self):
        return _("Deprecated, see remove")

    def _command_name(self):
        return "unsubscribe"

    def _primary(self):
        return False


class FactsCommand(CliCommand):

    def __init__(self):
        shortdesc = _("View or update the detected system information")
        super(FactsCommand, self).__init__("facts", shortdesc, False)

        self.parser.add_option("--list", action="store_true",
                               help=_("list known facts for this system"))
        self.parser.add_option("--update", action="store_true",
                               help=_("update the system facts"))

    def _validate_options(self):
        # Only require registration for updating facts
        if self.options.update:
            self.assert_should_be_registered()

        # if no relevant options, default to listing.
        if not (self.options.list or self.options.update):
            self.options.list = True

    def _do_command(self):
        self._validate_options()
        if self.options.list:
            facts = Facts(ent_dir=self.entitlement_dir,
                          prod_dir=self.product_dir)
            fact_dict = facts.get_facts()
            if ConsumerIdentity.exists():
                managerlib.enhance_facts(fact_dict, ConsumerIdentity.read())
            fact_keys = fact_dict.keys()
            fact_keys.sort()
            for key in fact_keys:
                value = fact_dict[key]
                if str(value).strip() == "":
                    value = _("Unknown")
                print "%s: %s" % (key, value)

        if self.options.update:
            facts = Facts(ent_dir=self.entitlement_dir,
                          prod_dir=self.product_dir)
            consumer = check_registration()['uuid']
            try:
                facts.update_check(self.cp, consumer, force=True)
            except connection.RestlibException, re:
                log.exception(re)
                system_exit(-1, re.msg)
            print _("Successfully updated the system facts.")


class ImportCertCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Import certificates which were provided outside of the tool")
        super(ImportCertCommand, self).__init__("import", shortdesc, False)

        self.parser.add_option("--certificate", action="append", dest="certificate_file",
                               help=_("certificate file to import (can be specified more than once)"))

    def _validate_options(self):
        if not self.options.certificate_file:
            print _("Error: This command requires that you specify a certificate with --certificate.")
            sys.exit(-1)

    def _add_common_options(self):
        # remove these options as per bz #733873
        return

    def _do_command(self):
        self._validate_options()
        # Return code
        imported = False
        for src_cert_file in self.options.certificate_file:
            if os.path.exists(src_cert_file):
                try:
                    extractor = managerlib.ImportFileExtractor(src_cert_file)

                    #Verify the entitlement data.
                    if extractor.verify_valid_entitlement():
                        extractor.write_to_disk()
                        print(_("Successfully imported certificate %s") %
                                    os.path.basename(src_cert_file))
                        imported = True
                    else:
                        log.error("Error parsing manually imported entitlement "
                            "certificate: %s" % src_cert_file)
                        print(_("%s is not a valid certificate file. Please use a valid certificate.") %
                                    os.path.basename(src_cert_file))

                except Exception, e:
                    # Should not get here unless something really bad happened.
                    log.exception(e)
                    print(_("An error occurred while importing the certificate. "
                            "Please check log file for more information."))
            else:
                log.error("Supplied certificate file does not exist: %s" % src_cert_file)
                print(_("%s is not a valid certificate file. Please use a valid certificate.") %
                    os.path.basename(src_cert_file))

        self._request_validity_check()

        return_code = 0
        if not imported:
            return_code = 1

        return return_code

    def require_connection(self):
        return False


class PluginsCommand(CliCommand):
    def __init__(self):
        shortdesc = _("View and configure subscription-manager plugins")
        super(PluginsCommand, self).__init__("plugins", shortdesc, False)

        self.parser.add_option("--list", action="store_true",
                                help=_("list subscription-manager plugins"))
        self.parser.add_option("--listslots", action="store_true",
                                help=_("list subscription-manager plugin slots"))
        self.parser.add_option("--listhooks", action="store_true",
                                help=_("list subscription-manager plugin hooks"))
        self.parser.add_option("--verbose", action="store_true",
                               default=False,
                               help=_("show verbose plugin info"))

    def _validate_options(self):
        # default to list
        if not (self.options.list or
                self.options.listslots or
                 self.options.listhooks):
            self.options.list = True

    def _add_common_options(self):
        pass

    def _list_plugins(self):
        for plugin_class in self.plugin_manager.get_plugins().values():
            enabled = _("disabled")
            if plugin_class.conf.is_plugin_enabled():
                enabled = _("enabled")
            print "%s: %s" % (plugin_class.get_plugin_key(), enabled)
            if self.options.verbose:
                print plugin_class.conf

    def _do_command(self):
        self._validate_options()

        if self.options.list:
            self._list_plugins()

        if self.options.listslots:
            for slot in self.plugin_manager.get_slots():
                print slot

        if self.options.listhooks:
            # get_slots is nicely sorted for presentation
            for slot in self.plugin_manager.get_slots():
                print slot
                for hook in sorted(self.plugin_manager._slot_to_funcs[slot]):
                    print "\t%s.%s" % (hook.im_class.get_plugin_key(), hook.__name__)


class ReposCommand(CliCommand):

    def __init__(self):
        shortdesc = _("List the repositories which this system is entitled to use")
        super(ReposCommand, self).__init__("repos", shortdesc, False)

        self.parser.add_option("--list", action="store_true",
                               help=_("list known repos for this system"))
        self.parser.add_option("--enable", dest="enable", metavar="REPOID",
                               action='append', help=_("repo to enable (can be specified more than once). Wildcards (* and ?) are supported."))
        self.parser.add_option("--disable", dest="disable", metavar="REPOID",
                               action='append', help=_("repo to disable (can be specified more than once). Wildcards (* and ?) are supported."))

    def _validate_options(self):
        if not (self.options.list or self.options.enable or self.options.disable):
            self.options.list = True

    def _do_command(self):
        self._validate_options()
        certmgr = CertManager(uep=self.cp)
        certmgr.update()
        rl = RepoLib(uep=self.cp)
        repos = rl.get_repos()
        rc = 0
        if cfg.has_option('rhsm', 'manage_repos') and \
                not int(cfg.get('rhsm', 'manage_repos')):
            print _("Repositories disabled by configuration.")
            return rc

        if self.options.enable:
            rc = rc or self._set_repo_status(repos, self.options.enable, True)
        if self.options.disable:
            rc = self._set_repo_status(repos, self.options.disable, False) or rc

        if self.options.list:
            if len(repos) > 0:
                print("+----------------------------------------------------------+")
                print _("    Available Repositories in %s") % rl.get_repo_file()
                print("+----------------------------------------------------------+")
                for repo in repos:
                    print columnize(REPOS_LIST, _echo,
                        repo.id,
                        repo["name"],
                        repo["baseurl"],
                        repo["enabled"]) + "\n"
            else:
                print _("This system has no repositories available through subscriptions.")
        return rc

    def _set_repo_status(self, repos, items, enable):
        repos_modified = []
        change_repos = []
        rc = 0
        if enable:
            status = '1'
        else:
            status = '0'

        for item in items:
            found = False
            contains_wildcard = self._contains_wildcard(item)
            for repo in repos:
                if fnmatch.fnmatch(repo.id, item):
                    if repo['enabled'] != status:
                        repo['enabled'] = status
                        change_repos.append(repo)
                    repos_modified.append(repo.id)
                    found = True
                    if not contains_wildcard:
                        break
            if not found:
                rc = 1
                print _("Error: %s is not a valid repo ID. "
                        "Use --list option to see valid repos.") % item
        if change_repos:
            repo_file = RepoFile()
            repo_file.read()
            for repo in change_repos:
                repo_file.update(repo)
            repo_file.write()
        for repo in repos_modified:
            if enable:
                print _("Repo %s is enabled for this system.") % repo
            else:
                print _("Repo %s is disabled for this system.") % repo
        return rc

    def _contains_wildcard(self, item):
        return "*" in item or \
            "?" in item or \
            "[" in item or \
            "!" in item or \
            "]" in item


class ConfigCommand(CliCommand):

    def __init__(self):
        shortdesc = _("List, set, or remove the configuration parameters in use by this system")
        super(ConfigCommand, self).__init__("config", shortdesc, False)

        self.parser.add_option("--list", action="store_true",
                               help=_("list the configuration for this system"))
        self.parser.add_option("--remove", dest="remove", action="append",
                               help=_("remove configuration entry by section.name"))
        for section in cfg.sections():
            for name, value in cfg.items(section):
                self.parser.add_option("--" + section + "." + name, dest=(section + "." + name),
                    help=_("Section: %s, Name: %s") % (section, name))

    def _add_common_options(self):
        pass

    def _validate_options(self):
        if self.options.list:
            too_many = False
            if self.options.remove:
                too_many = True
            else:
                for section in cfg.sections():
                    for name, value in cfg.items(section):
                        if getattr(self.options, section + "." + name):
                            too_many = True
                            break
            if too_many:
                sys.stderr.write(
                    _("Error: --list should not be used with any other options for setting or removing configurations.")
                )
                sys.stderr.write("\n")
                sys.exit(-1)

        if not (self.options.list or self.options.remove):
            has = False
            for section in cfg.sections():
                for name, value in cfg.items(section):
                    test = "%s" % getattr(self.options, section + "." + name)
                    has = has or (test != 'None')
            if not has:
                # if no options are given, default to --list
                self.options.list = True

        if self.options.remove:
            for r in self.options.remove:
                if not "." in r:
                    sys.stderr.write(
                        _("Error: configuration entry designation for removal must be of format [section.name]")
                    )
                    sys.stderr.write("\n")
                    sys.exit(-1)
                section = r.split('.')[0]
                name = r.split('.')[1]
                found = False
                if cfg.has_section(section):
                    for key, value in cfg.items(section):
                        if name == key:
                            found = True
                if not found:
                    sys.stderr.write(_("Error: Section %s and name %s does not exist.") % (section, name))
                    sys.exit(-1)

    def _do_command(self):
        self._validate_options()

        if self.options.list:
            for section in cfg.sections():
                print '[%s]' % (section)
                source_list = cfg.items(section)
                source_list.sort()
                for (name, value) in source_list:
                    indicator1 = ''
                    indicator2 = ''
                    if (value == cfg.defaults().get(name)):
                        indicator1 = '['
                        indicator2 = ']'
                    print '   %s = %s%s%s' % (name, indicator1, value, indicator2)
                print
            print _("[] - Default value in use")
            print ("\n")
        elif self.options.remove:
            for r in self.options.remove:
                section = r.split('.')[0]
                name = r.split('.')[1]
                try:
                    if not name in cfg.defaults().keys():
                        cfg.set(section, name, '')
                        print _("You have removed the value for section %s and name %s.") % (section, name)
                    else:
                        cfg.remove_option(section, name)
                        print _("You have removed the value for section %s and name %s.") % (section, name)
                        print _("The default value for %s will now be used.") % (name)
                except Exception:
                    print _("Section %s and name %s cannot be removed.") % (section, name)
            cfg.save()
        else:
            for section in cfg.sections():
                for name, value in cfg.items(section):
                    value = "%s" % getattr(self.options, section + "." + name)
                    if not value == 'None':
                        cfg.set(section, name, value)
            cfg.save()

    def require_connection(self):
        return False


class ListCommand(CliCommand):

    def __init__(self):
        shortdesc = _("List subscription and product information for this system")
        super(ListCommand, self).__init__("list", shortdesc, True)
        self.available = None
        self.consumed = None
        self.parser.add_option("--installed", action='store_true', help=_("list shows those products which are installed (default)"))
        self.parser.add_option("--available", action='store_true',
                               help=_("show those subscriptions which are available"))
        self.parser.add_option("--all", action='store_true',
                               help=_("used with --available to ensure all subscriptions are returned"))
        self.parser.add_option("--ondate", dest="on_date",
                                help=(_("date to search on, defaults to today's date, only used with --available (example: %s)")
                                      % strftime("%Y-%m-%d", localtime())))
        self.parser.add_option("--consumed", action='store_true',
                               help=_("show the subscriptions being consumed by this system"))
        self.parser.add_option("--servicelevel", dest="service_level",
                               help=_("shows only subscriptions matching the specified service level; only used with --available and --consumed"))

        self.facts = Facts(ent_dir=self.entitlement_dir,
                          prod_dir=self.product_dir)

    def _validate_options(self):
        if (self.options.all and not self.options.available):
            print _("Error: --all is only applicable with --available")
            sys.exit(-1)
        if (self.options.on_date and not self.options.available):
            print _("Error: --ondate is only applicable with --available")
            sys.exit(-1)
        if self.options.service_level is not None and not (self.options.consumed or
                                              self.options.available):
            print _("Error: --servicelevel is only applicable with --available or --consumed")
            sys.exit(-1)
        if not (self.options.available or self.options.consumed):
            self.options.installed = True

    def _do_command(self):
        """
        Executes the command.
        """

        self._validate_options()

        self.sorter = inj.require(inj.CERT_SORTER)

        if self.options.installed:
            iproducts = managerlib.get_installed_product_status(self.product_dir,
                    self.entitlement_dir, self.cp)
            if not len(iproducts):
                print(_("No installed products to list"))
                sys.exit(0)
            print "+-------------------------------------------+"
            print _("    Installed Product Status")
            print "+-------------------------------------------+"
            for product in iproducts:
                status = STATUS_MAP[product[4]]
                print columnize(INSTALLED_PRODUCT_STATUS, _none_wrap,
                                product[0], product[1], product[2], product[3],
                                status, product[5], product[6], product[7]) + "\n"

        if self.options.available:
            consumer = check_registration()['uuid']
            on_date = None
            if self.options.on_date:
                try:
                    # doing it this ugly way for pre python 2.5
                    on_date = datetime.datetime(
                            *(strptime(self.options.on_date, '%Y-%m-%d')[0:6]))
                except Exception:
                    print(_("Date entered is invalid. Date should be in YYYY-MM-DD format (example: ") + strftime("%Y-%m-%d", localtime()) + " )")
                    sys.exit(1)

            epools = managerlib.get_available_entitlements(self.cp, consumer,
                    self.facts, self.options.all, on_date)

            # Filter certs by service level, if specified.
            # Allowing "" here.
            if self.options.service_level is not None:
                epools = self._filter_pool_json_by_service_level(epools,
                                                    self.options.service_level)

            if not len(epools):
                print(_("No available subscription pools to list"))
                sys.exit(0)
            print("+-------------------------------------------+")
            print("    " + _("Available Subscriptions"))
            print("+-------------------------------------------+")
            for data in epools:
                if PoolWrapper(data).is_virt_only():
                    machine_type = machine_type = _("Virtual")
                else:
                    machine_type = _("Physical")

                print columnize(AVAILABLE_SUBS_LIST, _none_wrap,
                        data['productName'],
                        data['productId'],
                        data['id'],
                        data['quantity'],
                        data['service_level'] or "",
                        data['service_type'] or "",
                        data['multi-entitlement'],
                        data['endDate'],
                        machine_type) + "\n"

        if self.options.consumed:
            self.print_consumed(service_level=self.options.service_level)

    def _filter_pool_json_by_service_level(self, pools, service_level):

        def filter_pool_data_by_service_level(pool_data):
            pool_level = ""
            if pool_data['service_level']:
                pool_level = pool_data['service_level']

            return service_level.lower() == pool_level.lower()

        return filter(filter_pool_data_by_service_level, pools)

    def print_consumed(self, service_level=None):
        # list all certificates that have not yet expired, even those
        # that are not yet active.
        certs = [cert for cert in self.entitlement_dir.list() if not cert.is_expired()]

        # Filter certs by service level, if specified.
        # Allowing "" here.
        if service_level is not None:
            def filter_cert_by_service_level(cert):
                cert_level = ""
                if cert.order and cert.order.service_level:
                    cert_level = cert.order.service_level
                return service_level.lower() == \
                    cert_level.lower()
            certs = filter(filter_cert_by_service_level, certs)

        if len(certs) == 0:
            print(_("No consumed subscription pools to list"))
            sys.exit(0)

        cert_reasons_map = self.sorter.reasons.get_subscription_reasons_map()

        print("+-------------------------------------------+")
        print("   " + _("Consumed Subscriptions"))
        print("+-------------------------------------------+")

        for cert in certs:
            # for some certs, order can be empty
            # so we default the values and populate them if
            # they exist. BZ974587
            name = ""
            sku = ""
            contract = ""
            account = ""
            quantity_used = ""
            service_level = ""
            service_type = ""

            order = cert.order

            if order:
                service_level = order.service_level or ""
                service_type = order.service_type or ""
                name = order.name
                sku = order.sku
                contract = order.contract
                account = order.account
                quantity_used = order.quantity_used
                service_level = order.service_level
                service_type = order.service_type

            pool_id = _("Not Available")
            if hasattr(cert.pool, "id"):
                pool_id = cert.pool.id

            product_names = [p.name for p in cert.products]
            reasons = []
            if cert.subject and 'CN' in cert.subject and cert.subject['CN'] in cert_reasons_map:
                reasons = cert_reasons_map[cert.subject['CN']]
            print columnize(CONSUMED_LIST, _none_wrap,
                    name,
                    product_names,
                    sku,
                    contract,
                    account,
                    cert.serial,
                    pool_id,
                    cert.is_valid(),
                    quantity_used,
                    service_level,
                    service_type,
                    reasons,
                    managerlib.format_date(cert.valid_range.begin()),
                    managerlib.format_date(cert.valid_range.end())) + "\n"


class VersionCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Print version information")

        super(VersionCommand, self).__init__("version", shortdesc, False)

    def _add_common_options(self):
        pass

    def _do_command(self):
        # FIXME: slightly odd in that we log that we can't get the version,
        # but then show "unknown" here.
        print (_("server type: %s") % self.server_versions["server-type"])
        print (_("subscription management server: %s") % self.server_versions["candlepin"])
        print (_("subscription-manager: %s") % self.client_versions["subscription-manager"])
        print (_("python-rhsm: %s") % self.client_versions["python-rhsm"])


class StatusCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Show status information for this system's subscriptions and products")
        super(StatusCommand, self).__init__("status", shortdesc, True)

    def _add_common_options(self):
        pass

    def _do_command(self):
        # list status and all reasons it is not valid

        self.sorter = inj.require(inj.CERT_SORTER)

        print("+-------------------------------------------+")
        print("   " + _("System Status Details"))
        print("+-------------------------------------------+")

        if not self.is_registered():
            print(_("Overall Status: %s\n") % _("Unknown"))
            return

        overall_status = self.sorter.get_system_status()
        reasons = self.sorter.reasons.get_name_message_map()
        print(_("Overall Status: %s\n") % overall_status)

        columns = get_terminal_width()
        for name in reasons:
            print format_name(name + ':', 0, columns)
            for message in reasons[name]:
                print '- %s' % format_name(message, 2, columns)
            print ''


class ManagerCLI(CLI):

    def __init__(self):
        commands = [RegisterCommand, UnRegisterCommand, ConfigCommand, ListCommand,
                    SubscribeCommand, UnSubscribeCommand, FactsCommand,
                    IdentityCommand, OwnersCommand, RefreshCommand, CleanCommand,
                    RedeemCommand, ReposCommand, ReleaseCommand, StatusCommand,
                    EnvironmentsCommand, ImportCertCommand, ServiceLevelCommand,
                    VersionCommand, RemoveCommand, AttachCommand, PluginsCommand]
        CLI.__init__(self, command_classes=commands)

    def main(self):
        managerlib.check_identity_cert_perms()
        return CLI.main(self)


def width(in_str):
    if not isinstance(in_str, unicode):
        in_str = in_str.decode("utf-8")
    # From http://stackoverflow.com/questions/2476953/ user Josh Lee
    return sum(1 + (unicodedata.east_asian_width(c) in "WF") for c in in_str)


def ljust_wide(in_str, padding):
    return in_str + ' ' * (padding - width(in_str))


def columnize(caption_list, callback, *args):
    """
    Take a list of captions and values and columnize the output so that
    shorter captions are padded to be the same length as the longest caption.
    For example:
        Foo:            Bar
        Something Else: Baz

    This function also takes a callback which is used to render the final line.
    The callback gives us the ability to do things like replacing None values
    with the string "None" (see _none_wrap()).
    """
    padding = min(sorted(map(width, caption_list))[-1] + 1,
            int(get_terminal_width() / 2))
    padded_list = []
    for caption in caption_list:
        lines = format_name(caption, 0, padding - 1).split('\n')
        lines[-1] = ljust_wide(lines[-1], padding) + '%s'
        fixed_caption = '\n'.join(lines)
        padded_list.append(fixed_caption)

    lines = zip(padded_list, args)
    columns = get_terminal_width()
    output = []
    for (caption, value) in lines:
        if isinstance(value, list):
            if value:
                # Put the first value on the same line as the caption
                formatted_arg = format_name(value[0], padding, columns)
                output.append(callback(caption, formatted_arg))

                for val in value[1:]:
                    formatted_arg = format_name(val, padding, columns)
                    output.append(callback((" " * padding) + "%s", formatted_arg))
            else:
                # Degenerate case of an empty list
                output.append(callback(caption, ""))
        else:
            formatted_arg = format_name(value, padding, columns)
            output.append(callback(caption, formatted_arg))
    return '\n'.join(output)


def format_name(name, indent, max_length):
    """
    Formats a potentially long name for multi-line display, giving
    it a columned effect.  Assumes the first line is already
    properly indented.
    """
    if not name or not max_length or (max_length - indent) <= 2 or not isinstance(name, basestring):
        return name
    if not isinstance(name, unicode):
        name = name.decode("utf-8")
    words = name.split()
    current = indent
    lines = []
    # handle emtpty names
    if not words:
        return name

    def add_line():
        lines.append(' '.join(line))

    line = []
    # Split here and build it back up by word, this way we get word wrapping
    while words:
        word = words.pop(0)
        if current + width(word) <= max_length:
            current += width(word) + 1  # Have to account for the extra space
            line.append(word)
        else:
            if line:
                add_line()
            # If the word will not fit, break it
            if indent + width(word) > max_length:
                split_index = 0
                while(width(word[:split_index + 1]) + indent <= max_length):
                    split_index += 1
                words.insert(0, word[split_index:])
                word = word[:split_index]
            line = [word]
            if indent and lines:
                line.insert(0, ' ' * (indent - 1))
            current = indent + width(word) + 1

    add_line()
    return '\n'.join(lines)


def _none_wrap(template_str, *args):
    """
    Takes a template string and arguments and replaces any None arguments
    with the word "None" before rendering the template.  Mainly this is
    a callback meant to be used by columnize().
    """
    arglist = []
    for arg in args:
        if arg is None:
            arg = _("None")
        arglist.append(arg)
    return template_str % tuple(arglist)


def _echo(template_str, *args):
    """
    Just takes a template string and arguments and renders it.  Mainly
    this is a callback meant to be used by columnize().
    """
    return template_str % tuple(args)


# from http://farmdev.com/talks/unicode/
def to_unicode_or_bust(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def check_registration():
    if not ConsumerIdentity.existsAndValid():
        print(NOT_REGISTERED)
        sys.exit(-1)
    consumer = ConsumerIdentity.read()
    consumer_info = {"consumer_name": consumer.getConsumerName(),
                     "uuid": consumer.getConsumerId()}

    return consumer_info

if __name__ == "__main__":
    ManagerCLI().main()
