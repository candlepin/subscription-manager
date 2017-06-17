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
import fileinput
import fnmatch
import getpass
import gettext
import logging
from optparse import OptionValueError
import os
import re
import socket
import sys
from time import localtime, strftime, strptime

from M2Crypto import X509

import rhsm.config
import rhsm.connection as connection
from rhsm.utils import remove_scheme, ServerUrlParseError
from rhsm.certificate import GMT

from subscription_manager.branding import get_branding
from subscription_manager.entcertlib import EntCertActionInvoker
from subscription_manager.action_client import ActionClient, UnregisterActionClient
from subscription_manager.cert_sorter import ComplianceManager, FUTURE_SUBSCRIBED, \
        SUBSCRIBED, NOT_SUBSCRIBED, EXPIRED, PARTIALLY_SUBSCRIBED, UNKNOWN
from subscription_manager.cli import AbstractCLICommand, CLI, system_exit
from subscription_manager import rhelentbranding
from subscription_manager.hwprobe import ClassicCheck
import subscription_manager.injection as inj
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager import managerlib
from subscription_manager.managerlib import valid_quantity, format_date
from subscription_manager.release import ReleaseBackend
from subscription_manager.repolib import RepoActionInvoker, RepoFile, manage_repos_enabled
from subscription_manager.utils import parse_server_info, \
        parse_baseurl_info, format_baseurl, is_valid_server_info, \
        MissingCaCertException, get_client_versions, get_server_versions, \
        restart_virt_who, get_terminal_width, print_error, unique_list_items, \
        ProductCertificateFilter, EntitlementCertificateFilter
from subscription_manager.overrides import Overrides, Override
from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.printing_utils import columnize, format_name, \
        none_wrap_columnize_callback, echo_columnize_callback, highlight_by_filter_string_columnize_callback

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

cfg = rhsm.config.initConfig()

SM = "subscription-manager"
ERR_NOT_REGISTERED_MSG = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")
ERR_NOT_REGISTERED_CODE = 1

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
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Pool ID:"),
    _("Provides Management:"),
    _("Available:"),
    _("Suggested:"),
    _("Service Level:"),
    _("Service Type:"),
    _("Subscription Type:"),
    _("Ends:"),
    _("System Type:")
]

AVAILABLE_SUBS_MATCH_COLUMNS = [
    _("Subscription Name:"),
    _("Provides:"),
    _("SKU:"),
    _("Contract:"),
    _("Service Level:")
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
    _("Provides Management:"),
    _("Active:"),
    _("Quantity Used:"),
    _("Service Level:"),
    _("Service Type:"),
    _("Status Details:"),
    _("Subscription Type:"),
    _("Starts:"),
    _("Ends:"),
    _("System Type:")
]


def handle_exception(msg, ex):

    # On Python 2.4 and earlier, sys.exit triggers a SystemExit exception,
    # which can land us into this block of code. We do not want to handle
    # this or print any messages as the caller would already have done so,
    # so just re-throw and let Python have at it.
    if isinstance(ex, SystemExit):
        raise ex

    # GoneException will be handled uniformly for every command except unregister.
    if isinstance(ex, connection.GoneException):
        raise ex

    log.error(msg)
    log.exception(ex)

    exception_mapper = ExceptionMapper()
    mapped_message = exception_mapper.get_message(ex)
    if mapped_message:
        system_exit(os.EX_SOFTWARE, mapped_message)
    else:
        system_exit(os.EX_SOFTWARE, ex)


def autosubscribe(cp, consumer_uuid, service_level=None):
    """
    This is a wrapper for bind/bindByProduct. Eventually, we will exclusively
    use bind, but for now, we support both.
    """
    if service_level is not None:
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
    installed_status = get_installed_product_status(inj.require(inj.PROD_DIR),
            inj.require(inj.ENT_DIR), uep)

    if not installed_status:
        # Returning an error code here breaks registering when no products are installed, and the
        # AttachCommand already performs this check before calling.
        print _("No products installed.")
        return 0

    log.info("Attempted to auto-attach/heal the system.")
    print _("Installed Product Current Status:")
    subscribed = 1
    all_subscribed = True
    for prod_status in installed_status:
        if prod_status[4] == SUBSCRIBED:
            subscribed = 0
        status = STATUS_MAP[prod_status[4]]
        if prod_status[4] == NOT_SUBSCRIBED:
            all_subscribed = False
        print columnize(PRODUCT_STATUS, echo_columnize_callback, prod_status[0], status) + "\n"
    if not all_subscribed:
        print _("Unable to find available subscriptions for all your installed products.")
    return subscribed


def get_installed_product_status(product_directory, entitlement_directory, uep, filter_string=None):
    """
     Returns the Installed products and their subscription states
    """
    product_status = []

    calculator = inj.require(inj.PRODUCT_DATE_RANGE_CALCULATOR, uep)
    sorter = inj.require(inj.CERT_SORTER)
    cert_filter = None

    if filter_string is not None:
        cert_filter = ProductCertificateFilter(filter_string)

    print

    for installed_product in sorter.installed_products:
        product_cert = sorter.installed_products[installed_product]

        if cert_filter is None or cert_filter.match(product_cert):
            for product in product_cert.products:
                begin = ""
                end = ""
                prod_status_range = calculator.calculate(product.id)

                if prod_status_range:
                    # Format the date in user's local time as the date
                    # range is returned in GMT.
                    begin = format_date(prod_status_range.begin())
                    end = format_date(prod_status_range.end())

                product_status.append((
                    product.name,
                    installed_product,
                    product.version,
                    ",".join(product.architectures),
                    sorter.get_status(product.id),
                    sorter.reasons.get_product_reasons(product),
                    begin,
                    end
                ))

    return product_status


class CliCommand(AbstractCLICommand):
    """ Base class for all sub-commands. """

    def __init__(self, name="cli", shortdesc=None, primary=False):
        AbstractCLICommand.__init__(self, name=name, shortdesc=shortdesc, primary=primary)

        self.log = self._get_logger()

        if self.require_connection():
            self._add_proxy_options()

        self.server_url = None

        # TODO
        self.server_hostname = None
        self.server_port = None
        self.server_prefix = None
        self.proxy_user = None
        self.proxy_password = None
        #
        self.proxy_url = None
        self.proxy_hostname = None
        self.proxy_port = None

        self.entitlement_dir = inj.require(inj.ENT_DIR)
        self.product_dir = inj.require(inj.PROD_DIR)

        self.client_versions = self._default_client_version()
        self.server_versions = self._default_server_version()

        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)

        self.identity = inj.require(inj.IDENTITY)

    def _get_logger(self):
        return logging.getLogger('rhsm-app.%s.%s' % (self.__module__, self.__class__.__name__))

    def test_proxy_connection(self):
        result = None
        if not self.proxy_hostname or cfg.get("server", "proxy_hostname"):
            return True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            result = s.connect_ex((self.proxy_hostname or cfg.get("server", "proxy_hostname"), int(self.proxy_port or rhsm.config.DEFAULT_PROXY_PORT)))
        except Exception as e:
            log.info("Attempted bad proxy: %s" % e)
        finally:
            s.close()
        if result:
            return False
        else:
            return True

    def _request_validity_check(self):
        # Make sure the sorter is fresh (low footprint if it is)
        inj.require(inj.CERT_SORTER).force_cert_check()
        inj.require(inj.DBUS_IFACE).update()

    def _add_url_options(self):
        """ Add options that allow the setting of the server URL."""
        self.parser.add_option("--serverurl", dest="server_url",
                               default=None, help=_("server URL in the form of https://hostname:port/prefix"))
        self.parser.add_option("--insecure", action="store_true",
                                default=False, help=_("do not check the entitlement server SSL certificate against available certificate authorities"))

    def _add_proxy_options(self):
        """ Add proxy options that apply to sub-commands that require network connections. """
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
            system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)

    def is_registered(self):
        self.identity = inj.require(inj.IDENTITY)
        log.info('%s', self.identity)
        return self.identity.is_valid()

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
                "rules-type": _("Unknown"),
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
        self.server_versions = get_server_versions(self.no_auth_cp, exception_on_timeout=True)
        log.info("Server Versions: %s" % self.server_versions)

    def main(self, args=None):

        # TODO: For now, we disable the CLI entirely. We may want to allow some commands in the future.
        if rhsm.config.in_container():
            system_exit(os.EX_CONFIG, _("subscription-manager is disabled when running inside a container. Please refer to your host system for subscription management.\n"))

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
            system_exit(os.EX_USAGE)

        if hasattr(self.options, "insecure") and self.options.insecure:
            cfg.set("server", "insecure", "1")
            config_changed = True

        if hasattr(self.options, "server_url") and self.options.server_url:
            try:
                (self.server_hostname,
                 self.server_port,
                 self.server_prefix) = parse_server_info(self.options.server_url, cfg)
            except ServerUrlParseError, e:
                print _("Error parsing serverurl:")
                handle_exception("Error parsing serverurl:", e)
            # this trys to actually connect to the server and ping it
            try:
                if not is_valid_server_info(self.server_hostname, self.server_port, self.server_prefix):
                    system_exit(os.EX_UNAVAILABLE, _("Unable to reach the server at %s:%s%s") % (
                        self.server_hostname,
                        self.server_port,
                        self.server_prefix
                    ))
            except MissingCaCertException:
                system_exit(os.EX_CONFIG, _("Error: CA certificate for subscription service has not been installed."))

            cfg.set("server", "hostname", self.server_hostname)
            cfg.set("server", "port", self.server_port)
            cfg.set("server", "prefix", self.server_prefix)
            if self.server_port:
                self.server_port = int(self.server_port)
            config_changed = True

        if hasattr(self.options, "base_url") and self.options.base_url:
            try:
                (baseurl_server_hostname,
                 baseurl_server_port,
                 baseurl_server_prefix) = parse_baseurl_info(self.options.base_url)
            except ServerUrlParseError, e:
                print _("Error parsing baseurl:")
                handle_exception("Error parsing baseurl:", e)

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
            config_changed = True

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

            self.entcertlib = EntCertActionInvoker()

            if config_changed:
                if not self.test_proxy_connection():
                    system_exit(os.EX_UNAVAILABLE, _("Proxy connection failed, please check your settings."))

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
            system_exit(os.EX_SOFTWARE, _('System certificates corrupted. Please reregister.'))
        except connection.GoneException, ge:
            if ge.deleted_id == self.identity.uuid:
                log.critical("Consumer profile \"%s\" has been deleted from the server.", self.identity.uuid)
                system_exit(os.EX_UNAVAILABLE, _("Consumer profile \"%s\" has been deleted from the server. You can use command clean or unregister to remove local profile.") % self.identity.uuid)
            else:
                raise ge


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
        while not username:
            username = raw_input(_("Username: "))
        while not password:
            password = getpass.getpass(_("Password: "))
        return (username.strip(), password.strip())

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
        self.assert_should_be_registered()
        try:
            self.entcertlib.update()
            log.info("Refreshed local data")
            print (_("All local data refreshed"))
        except connection.RestlibException, re:
            log.error(re)
            system_exit(os.EX_SOFTWARE, re.msg)
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
                               help=_("force certificate regeneration (requires username and password); Only used with --regenerate"))

    def _validate_options(self):
        self.assert_should_be_registered()
        if self.options.force and not self.options.regenerate:
            system_exit(os.EX_USAGE, _("--force can only be used with --regenerate"))
        if (self.options.username or self.options.password) and not self.options.force:
            system_exit(os.EX_USAGE, _("--username and --password can only be used with --force"))

    def _do_command(self):
        # get current consumer identity
        identity = inj.require(inj.IDENTITY)

        # check for Classic before doing anything else
        if ClassicCheck().is_registered_with_classic():
            if identity.is_valid():
                print _("server type: %s") % get_branding().REGISTERED_TO_BOTH_SUMMARY
            else:
                # no need to continue if user is only registered to Classic
                print _("server type: %s") % get_branding().REGISTERED_TO_OTHER_SUMMARY
                return

        try:
            self._validate_options()
            consumerid = self.identity.uuid
            consumer_name = self.identity.name
            if not self.options.regenerate:
                owner = self.cp.getOwner(consumerid)
                ownername = owner['displayName']
                ownerid = owner['key']

                print _('system identity: %s') % consumerid
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

                # do this in persist_consumer_cert? or some other
                # high level, "I just registered" thing
                self.identity.reload()

                print _("Identity certificate has been regenerated.")

                log.info("Successfully generated a new identity from server.")
        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to generate a new identity for the system: %s" % re)
            system_exit(os.EX_SOFTWARE, re.msg)
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
                    print columnize(ORG_LIST, echo_columnize_callback,
                            owner['displayName'], owner['key']) + "\n"
            else:
                print(_("%s cannot register with any organizations.") % self.username)

        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to retrieve org list from server: %s" % re)
            system_exit(os.EX_SOFTWARE, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to retrieve org list from server"), e)


class EnvironmentsCommand(OrgCommand):

    def __init__(self):
        shortdesc = _("Display the environments available for a user")
        self._org_help_text = _("specify organization for environment list, using organization key")

        super(EnvironmentsCommand, self).__init__("environments", shortdesc,
                                                  False)
        self._add_url_options()

    def _get_enviornments(self, org):
        return self.cp.getEnvironmentList(org)

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
                        print columnize(ENVIRONMENT_LIST, echo_columnize_callback, env['name'],
                                env['description'] or "") + "\n"
                else:
                    print _("This org does not have any environments.")
            else:
                system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support environments."))

            log.info("Successfully retrieved environment list from server.")
        except connection.RestlibException, re:
            log.exception(re)
            log.error(u"Error: Unable to retrieve environment list from server: %s" % re)
            system_exit(os.EX_SOFTWARE, re.msg)
        except Exception, e:
            handle_exception(_("Error: Unable to retrieve environment list from server"), e)


class AutohealCommand(CliCommand):

    def __init__(self):
        self.uuid = inj.require(inj.IDENTITY).uuid

        shortdesc = _("Set if subscriptions are attached on a schedule (default of daily)")
        self._org_help_text = _("specify whether to enable or disable auto-attaching of subscriptions")
        super(AutohealCommand, self).__init__("auto-attach", shortdesc,
                                                False)

        self.parser.add_option("--enable", dest="enable", action='store_true',
                help=_("try to attach subscriptions for uncovered products each check-in"))
        self.parser.add_option("--disable", dest="disable", action='store_true',
                help=_("do not try to automatically attach subscriptions each check-in"))
        self.parser.add_option("--show", dest="show", action='store_true',
                help=_("show the current auto-attach preference"))

    def _toggle(self, autoheal):
        self.cp.updateConsumer(self.uuid, autoheal=autoheal)
        self._show(autoheal)

    def _validate_options(self):
        if not self.uuid:
            self.assert_should_be_registered()

    def _show(self, autoheal):
        if autoheal:
            print _("Auto-attach preference: enabled")
        else:
            print _("Auto-attach preference: disabled")

    def _do_command(self):
        self._validate_options()

        if not self.options.enable and not self.options.disable:
            self._show(self.cp.getConsumer(self.uuid)['autoheal'])
        else:
            self._toggle(self.options.enable or False)


class ServiceLevelCommand(OrgCommand):

    def __init__(self):

        shortdesc = _("Manage service levels for this system")
        self._org_help_text = _("specify an organization when listing available service levels using the organization key, only used with --list")
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

        self.identity = inj.require(inj.IDENTITY)

    def _set_service_level(self, service_level):
        consumer = self.cp.getConsumer(self.identity.uuid)
        if 'serviceLevel' not in consumer:
            system_exit(os.EX_UNAVAILABLE, _("Error: The service-level command is not supported by the server."))
        self.cp.updateConsumer(self.identity.uuid, service_level=service_level)

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

        if self.options.org and not self.options.list:
            system_exit(os.EX_USAGE, _("Error: --org is only supported with the --list option"))

        if not self.is_registered():
            if self.options.list:
                if not (self.options.username and self.options.password):
                    system_exit(os.EX_USAGE, _("Error: you must register or specify --username and --password to list service levels"))
            else:
                system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)

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
            system_exit(os.EX_SOFTWARE, re.msg)
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
        consumer = self.cp.getConsumer(self.identity.uuid)
        if 'serviceLevel' not in consumer:
            system_exit(os.EX_UNAVAILABLE, _("Error: The service-level command is not supported by the server."))
        service_level = consumer['serviceLevel'] or ""
        if service_level:
            print(_("Current service level: %s") % service_level)
        else:
            print _("Service level preference not set")

    def list_service_levels(self):
        org_key = self.options.org
        if not org_key:
            if self.is_registered():
                org_key = self.cp.getOwner(self.identity.uuid)['key']
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
            system_exit(os.EX_UNAVAILABLE, _("Error: The service-level command is not supported by the server."))
        except connection.RestlibException, e:
            if e.code == 404 and e.msg.find('/servicelevels') > 0:
                system_exit(os.EX_UNAVAILABLE, _("Error: The service-level command is not supported by the server."))
            else:
                raise e


class RegisterCommand(UserPassCommand):
    def __init__(self):
        shortdesc = get_branding().CLI_REGISTER

        super(RegisterCommand, self).__init__("register", shortdesc, True)

        self._add_url_options()
        self.parser.add_option("--baseurl", dest="base_url",
                              default=None, help=_("base URL for content in form of https://hostname:port/prefix"))
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
                               help=_("system preference used when subscribing automatically, requires --auto-attach"))

    def _validate_options(self):
        self.autoattach = self.options.autosubscribe or self.options.autoattach
        if self.is_registered() and not self.options.force:
            system_exit(os.EX_USAGE, _("This system is already registered. Use --force to override"))
        elif (self.options.consumername == ''):
            system_exit(os.EX_USAGE, _("Error: system name can not be empty."))
        elif (self.options.username and self.options.activation_keys):
            system_exit(os.EX_USAGE, _("Error: Activation keys do not require user credentials."))
        elif (self.options.consumerid and self.options.activation_keys):
            system_exit(os.EX_USAGE, _("Error: Activation keys can not be used with previously registered IDs."))
        elif (self.options.environment and self.options.activation_keys):
            system_exit(os.EX_USAGE, _("Error: Activation keys do not allow environments to be specified."))
        elif (self.autoattach and self.options.activation_keys):
            system_exit(os.EX_USAGE, _("Error: Activation keys cannot be used with --auto-attach."))
        # 746259: Don't allow the user to pass in an empty string as an activation key
        elif (self.options.activation_keys and '' in self.options.activation_keys):
            system_exit(os.EX_USAGE, _("Error: Must specify an activation key"))
        elif (self.options.service_level and not self.autoattach):
            system_exit(os.EX_USAGE, _("Error: Must use --auto-attach with --servicelevel."))
        elif (self.options.activation_keys and not self.options.org):
            system_exit(os.EX_USAGE, _("Error: Must provide --org with activation keys."))
        elif (self.options.force and self.options.consumerid):
            system_exit(os.EX_USAGE, _("Error: Can not force registration while attempting to recover registration with consumerid. Please use --force without --consumerid to re-register or use the clean command and try again without --force."))

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
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)

        # Set consumer's name to hostname by default:
        consumername = self.options.consumername
        if consumername is None:
            consumername = socket.gethostname()

        if self.is_registered() and self.options.force:
            # First let's try to un-register previous consumer. This may fail
            # if consumer has already been deleted so we will continue even if
            # errors are encountered.
            old_uuid = self.identity.uuid
            try:
                managerlib.unregister(self.cp, old_uuid)
                self.entitlement_dir.__init__()
                self.product_dir.__init__()
                log.info("--force specified, unregistered old consumer: %s" % old_uuid)
                print(_("The system with UUID %s has been unregistered") % old_uuid)
            except Exception, e:
                log.error("Unable to unregister consumer: %s" % old_uuid)
                log.exception(e)

        self.cp_provider.clean()

        facts = inj.require(inj.FACTS)

        # Proceed with new registration:
        try:
            if not self.options.activation_keys:
                print _("Registering to: %s:%s%s") % \
                    (cfg.get("server", "hostname"), cfg.get("server", "port"), cfg.get("server", "prefix"))
                self.cp_provider.set_user_pass(self.username, self.password)
                admin_cp = self.cp_provider.get_basic_auth_cp()
            else:
                admin_cp = self.cp_provider.get_no_auth_cp()

            facts_dic = facts.get_facts()

            self.plugin_manager.run("pre_register_consumer", name=consumername,
                                    facts=facts_dic)

            if self.options.consumerid:
                # TODO remove the username/password
                log.info("Registering as existing consumer: %s" %
                        self.options.consumerid)
                consumer = admin_cp.getConsumer(self.options.consumerid,
                        self.username, self.password)

                if 'type' not in consumer:
                    log.warn('Unable to determine consumer type, proceeding with registration.')

                if consumer.get('type', {}).get('manifest', {}):
                    log.error("registration attempted with consumerid = Subscription Management Application's uuid: %s" % self.options.consumerid)
                    system_exit(os.EX_USAGE, _("Error: Cannot register with an ID of a Subscription Management Application: %s" % self.options.consumerid))

            else:
                owner_key = self._determine_owner_key(admin_cp)

                environment_id = self._get_environment_id(admin_cp, owner_key,
                        self.options.environment)

                consumer = admin_cp.registerConsumer(name=consumername,
                     type=self.options.consumertype, facts=facts_dic,
                     owner=owner_key, environment=environment_id,
                     keys=self.options.activation_keys,
                     installed_products=self.installed_mgr.format_for_server(),
                     content_tags=self.installed_mgr.tags)
                self.installed_mgr.write_cache()
            self.plugin_manager.run("post_register_consumer", consumer=consumer,
                                    facts=facts_dic)
        except connection.RestlibException, re:
            log.exception(re)
            system_exit(os.EX_SOFTWARE, re.msg)
        except Exception, e:
            handle_exception(_("Error during registration: %s") % e, e)

        consumer_info = self._persist_identity_cert(consumer)

        # We have new credentials, restart virt-who
        restart_virt_who()

        print (_("The system has been registered with ID: %s ")) % (consumer_info["uuid"])

        # get a new UEP as the consumer
        self.cp = self.cp_provider.get_consumer_auth_cp()

        # Reload the consumer identity:
        self.identity.reload()

        # log the version of the server we registered to
        self.log_server_version()

        # FIXME: can these cases be replaced with invoking
        # FactsLib (or a FactsManager?)
        # Must update facts to clear out the old ones:
        if self.options.consumerid:
            log.info("Updating facts")
            facts.update_check(self.cp, consumer['uuid'], force=True)

        profile_mgr = inj.require(inj.PROFILE_MANAGER)
        # 767265: always force an upload of the packages when registering
        profile_mgr.update_check(self.cp, consumer['uuid'], True)

        # Facts and installed products went out with the registration request,
        # manually write caches to disk:
        facts.write_cache()
        self.installed_mgr.update_check(self.cp, consumer['uuid'])

        if self.options.release:
            # TODO: grab the list of valid options, and check
            self.cp.updateConsumer(consumer['uuid'], release=self.options.release)

        if self.autoattach:
            if 'serviceLevel' not in consumer and self.options.service_level:
                system_exit(os.EX_UNAVAILABLE, _("Error: The --servicelevel option is not supported "
                                 "by the server. Did not complete your request."))
            try:
                autosubscribe(self.cp, consumer['uuid'], service_level=self.options.service_level)
            except connection.RestlibException, re:
                print_error(re.msg)

        if (self.options.consumerid or self.options.activation_keys or self.autoattach):
            log.info("System registered, updating entitlements if needed")
            # update certs, repos, and caches.
            # FIXME: aside from the overhead, should this be cert_action_client.update?
            self.entcertlib.update()

        subscribed = 0
        if (self.options.activation_keys or self.autoattach):
            # update with latest cert info
            self.sorter = inj.require(inj.CERT_SORTER)
            self.sorter.force_cert_check()
            subscribed = show_autosubscribe_output(self.cp)

        self._request_validity_check()
        return subscribed

    def _persist_identity_cert(self, consumer):
        """
        Parses the consumer dict returned from the cert, pulls out the identity
        certificate, and writes to disk.
        """
        return managerlib.persist_consumer_cert(consumer)

    def _prompt_for_environment(self):
        """
        By breaking this code out, we can write cleaner tests
        """
        return raw_input(_("Environment: ")).strip() or self._prompt_for_environment()

    def _get_environment_id(self, cp, owner_key, environment_name):
        # If none specified on CLI and the server doesn't support environments,
        # return None, the registration method will skip environment specification.

        # Activation keys may not be used with environment for registration.
        # We use a no-auth cp, so we cannot look up environment ids by name
        if self.options.activation_keys:
            return None

        supports_environments = cp.supports_resource('environments')
        if not environment_name:
            if supports_environments:
                env_list = cp.getEnvironmentList(owner_key)

                # If there aren't any environments, don't prompt for one
                if not env_list:
                    return environment_name

                # If the envronment list is len 1, pick that environment
                if len(env_list) == 1:
                    log.debug('Using the only available environment: "%s"' % env_list[0]['name'])
                    return env_list[0]['id']

                environment_name = self._prompt_for_environment()

                # Should only ever be len 0 or 1
                env_matches = [env['id'] for env in env_list if env['name'] == environment_name]
                if env_matches:
                    return env_matches[0]
                system_exit(os.EX_DATAERR, _("No such environment: %s") % environment_name)

            # Server doesn't support environments
            return environment_name

        if not supports_environments:
            system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support environments."))

        env = cp.getEnvironment(owner_key=owner_key, name=environment_name)
        if not env:
            system_exit(os.EX_DATAERR, _("No such environment: %s") % environment_name)
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
            system_exit(1, _("%s cannot register with any organizations.") % self.username)
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
        if not self.is_registered():
            # TODO: Should this use the standard NOT_REGISTERED message?
            system_exit(ERR_NOT_REGISTERED_CODE, _("This system is currently not registered."))

        try:
            managerlib.unregister(self.cp, self.identity.uuid)
        except Exception, e:
            handle_exception("Unregister failed", e)

        # managerlib.unregister reloads the now None provided identity
        # so cp_provider provided auth_cp's should fail, like the below

        #this block is simply to ensure that the yum repos got updated. If it fails,
        #there is no issue since it will most likely be cleaned up elsewhere (most
        #likely by the yum plugin)
        try:
            # there is no consumer cert at this point, a uep object
            # is not useful
            cleanup_certmgr = UnregisterActionClient()
            cleanup_certmgr.update()
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
            system_exit(os.EX_USAGE, _("Error: This command requires that you specify an email address with --email."))

    def _do_command(self):
        """
        Executes the command.
        """
        self.assert_should_be_registered()

        self._validate_options()

        try:
            # FIXME: why just facts and package profile update here?
            # update facts first, if we need to
            facts = inj.require(inj.FACTS)
            facts.update_check(self.cp, self.identity.uuid)

            profile_mgr = inj.require(inj.PROFILE_MANAGER)
            profile_mgr.update_check(self.cp, self.identity.uuid)

            # BZ 1248833 Ensure we print out the display message if we get any back
            response = self.cp.activateMachine(self.identity.uuid, self.options.email, self.options.locale)
            if response and response.get('displayMessage'):
                system_exit(0, response.get('displayMessage'))

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
        consumer = self.cp.getConsumer(self.identity.uuid)
        if 'releaseVer' not in consumer:
            system_exit(os.EX_UNAVAILABLE, err_msg)
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

        # Base CliCommand has already setup proxy info etc
        self.cp_provider.set_content_connection_info(cdn_hostname=cdn_hostname,
                                                     cdn_port=cdn_port)
        self.release_backend = ReleaseBackend()

        self.assert_should_be_registered()

        if self.options.unset:
            self.cp.updateConsumer(self.identity.uuid,
                        release="")
            print _("Release preference has been unset")
        elif self.options.release is not None:
            # check first if the server supports releases
            self._get_consumer_release()
            releases = self.release_backend.get_releases()
            if self.options.release in releases:
                self.cp.updateConsumer(self.identity.uuid,
                        release=self.options.release)
            else:
                system_exit(os.EX_DATAERR, _("No releases match '%s'.  "
                                 "Consult 'release --list' for a full listing.")
                                 % self.options.release)
            print _("Release set to: %s") % self.options.release
        elif self.options.list:
            self._get_consumer_release()
            releases = self.release_backend.get_releases()
            if not releases:
                system_exit(os.EX_CONFIG, _("No release versions available, please check subscriptions."))

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
        self.auto_attach = True
        self.parser.add_option("--pool", dest="pool", action='append',
                               help=_("The ID of the pool to attach (can be specified more than once)"))
        self.parser.add_option("--quantity", dest="quantity",
            help=_("Number of subscriptions to attach. May not be used with an auto-attach."))
        self.parser.add_option("--auto", action='store_true',
            help=_("Automatically attach compatible subscriptions to this system. This is the default action."))
        self.parser.add_option("--servicelevel", dest="service_level",
                               help=_("Automatically attach only subscriptions matching the specified service level; only used with --auto"))
        self.parser.add_option("--file", dest="file",
                                help=_("A file from which to read pool IDs. If a hyphen is provided, pool IDs will be read from stdin."))

        # re bz #864207
        _("All installed products are covered by valid entitlements.")
        _("No need to update subscriptions at this time.")

    def _read_pool_ids(self, file):
        if not self.options.pool:
            self.options.pool = []

        for line in fileinput.input(file):
            for pool in filter(bool, re.split(r"\s+", line.strip())):
                self.options.pool.append(pool)

    def _short_description(self):
        return _("Attach a specified subscription to the registered system")

    def _command_name(self):
        return "attach"

    def _primary(self):
        return True

    def _validate_options(self):
        if self.options.pool or self.options.file:
            if self.options.auto:
                system_exit(os.EX_USAGE, _("Error: --auto may not be used when specifying pools."))
            if self.options.service_level:
                system_exit(os.EX_USAGE, _("Error: The --servicelevel option cannot be used when specifying pools."))

        # Quantity must be a positive integer
        # TODO: simplify with a optparse type="int"
        quantity = self.options.quantity
        if self.options.quantity:
            if not valid_quantity(quantity):
                system_exit(os.EX_USAGE, _("Error: Quantity must be a positive integer."))
            elif self.options.auto or not (self.options.pool or self.options.file):
                system_exit(os.EX_USAGE, _("Error: --quantity may not be used with an auto-attach"))
            else:
                self.options.quantity = int(self.options.quantity)

        # If a pools file was specified, process its contents and append it to options.pool
        if self.options.file:
            if self.options.file == '-' or os.path.isfile(self.options.file):
                self._read_pool_ids(self.options.file)

                if len(self.options.pool) < 1:
                    if self.options.file == '-':
                        system_exit(os.EX_DATAERR, _("Error: Received data does not contain any pool IDs."))
                    else:
                        system_exit(os.EX_DATAERR, _("Error: The file \"%s\" does not contain any pool IDs.") % self.options.file)
            else:
                system_exit(os.EX_DATAERR, _("Error: The file \"%s\" does not exist or cannot be read.") % self.options.file)

    def _do_command(self):
        """
        Executes the command.
        """
        self.assert_should_be_registered()
        self._validate_options()

        # --pool or --file turns off default auto attach
        if self.options.pool or self.options.file:
            self.auto_attach = False

        # TODO: change to if self.auto_attach: else: pool/file stuff
        try:
            cert_action_client = ActionClient()
            cert_action_client.update()
            return_code = 0
            cert_update = True
            if self.options.pool:
                subscribed = False
                for pool in self.options.pool:
                    try:
                        # odd html strings will cause issues, reject them here.
                        if (pool.find("#") >= 0):
                            system_exit(os.EX_USAGE, _("Please enter a valid numeric pool ID."))
                        # If quantity is None, server will assume 1. pre_subscribe will
                        # report the same.
                        self.plugin_manager.run("pre_subscribe",
                                                consumer_uuid=self.identity.uuid,
                                                pool_id=pool,
                                                quantity=self.options.quantity)
                        ents = self.cp.bindByEntitlementPool(self.identity.uuid, pool, self.options.quantity)
                        self.plugin_manager.run("post_subscribe", consumer_uuid=self.identity.uuid, entitlement_data=ents)
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
                        elif re.code == 400 or re.code == 404:
                            print re.msg  # no such pool.
                        else:
                            system_exit(os.EX_SOFTWARE, re.msg)  # some other error.. don't try again
                if not subscribed:
                    return_code = 1
            # must be auto
            else:
                products_installed = len(get_installed_product_status(self.product_dir,
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
                        consumer = self.cp.getConsumer(self.identity.uuid)
                        if 'serviceLevel' not in consumer:
                            system_exit(os.EX_UNAVAILABLE, _("Error: The --servicelevel option is not "
                                             "supported by the server. Did not "
                                             "complete your request."))
                    autosubscribe(self.cp, self.identity.uuid,
                                  service_level=self.options.service_level)
            report = None
            if cert_update:
                report = self.entcertlib.update()

            if report and report.exceptions():
                print _('Entitlement Certificate(s) update failed due to the following reasons:')
                for e in report.exceptions():
                    print '\t-', str(e)
            elif self.auto_attach:
                if not products_installed:
                    return_code = 1
                else:
                    self.sorter.force_cert_check()
                    # run this after entcertlib update, so we have the new entitlements
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
        self.parser.add_option("--pool", action='append', dest="pool_ids", metavar="POOL_ID",
                       help=_("the ID of the pool to remove (can be specified more than once)"))
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
                system_exit(os.EX_USAGE)
        elif self.options.pool_ids:
            if not self.cp.has_capability("remove_by_pool_id"):
                system_exit(os.EX_UNAVAILABLE, _("Error: The registered entitlement server does not support remove --pool."
                        "\nInstead, use the remove --serial option."))
        elif not self.options.all and not self.options.pool_ids:
            system_exit(os.EX_USAGE, _("Error: This command requires that you specify one of --serial, --pool or --all."))

    def _unbind_ids(self, unbind_method, consumer_uuid, ids):
        success = []
        failure = []
        for id_ in ids:
            try:
                unbind_method(consumer_uuid, id_)
                success.append(id_)
            except connection.RestlibException, re:
                if re.code == 410:
                    system_exit(os.EX_SOFTWARE, re.msg)
                failure.append(id_)
                log.error(re)
        return (success, failure)

    def _print_unbind_ids_result(self, success, failure, id_name):
        if success:
            if id_name == "pools":
                print _("The entitlement server successfully removed these pools:")
            elif id_name == "serial numbers":
                print _("The entitlement server successfully removed these serial numbers:")
            else:
                print _("The entitlement server successfully removed these IDs:")
            for id_ in success:
                print "   %s" % id_
        if failure:
            if id_name == "pools":
                print _("The entitlement server failed to remove these pools:")
            elif id_name == "serial numbers":
                print _("The entitlement server failed to remove these serial numbers:")
            else:
                print _("The entitlement server failed to remove these IDs:")
            for id_ in failure:
                print "   %s" % id_

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        return_code = 0
        if self.is_registered():
            identity = inj.require(inj.IDENTITY)
            try:
                if self.options.all:
                    total = self.cp.unbindAll(identity.uuid)
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
                    removed_serials = []
                    if self.options.pool_ids:
                        pool_ids = unique_list_items(self.options.pool_ids)  # Don't allow duplicates
                        pool_id_to_serials = self.entitlement_dir.list_serials_for_pool_ids(pool_ids)
                        success, failure = self._unbind_ids(self.cp.unbindByPoolId, identity.uuid, pool_ids)
                        self._print_unbind_ids_result(success, failure, "pools")
                        if not success:
                            return_code = 1
                        else:
                            for pool_id in success:
                                removed_serials.extend(pool_id_to_serials[pool_id])
                    success = []
                    failure = []  # Clear this list to make sure we don't display the pool ids as serial
                    if self.options.serials:
                        serials = unique_list_items(self.options.serials)
                        serials_to_remove = [serial for serial in serials if serial not in removed_serials]  # Don't remove serials already removed by a pool
                        success, failure = self._unbind_ids(self.cp.unbindBySerial, identity.uuid, serials_to_remove)
                        removed_serials.extend(success)
                        if not success:
                            return_code = 1
                    self._print_unbind_ids_result(removed_serials, failure, "serial numbers")
                self.entcertlib.update()
            except connection.RestlibException, re:
                log.error(re)
                system_exit(os.EX_SOFTWARE, re.msg)
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
                    if self.options.serials or self.options.pool_ids:
                        serials = self.options.serials or []
                        pool_ids = self.options.pool_ids or []
                        count = 0
                        for ent in self.entitlement_dir.list():
                            ent_pool_id = str(getattr(ent.pool, 'id', None) or "")
                            if str(ent.serial) in serials or ent_pool_id in pool_ids:
                                ent.delete()
                                print _("Subscription with serial number %s removed from this system") % str(ent.serial)
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

        identity = inj.require(inj.IDENTITY)
        if self.options.list:
            facts = inj.require(inj.FACTS)
            fact_dict = facts.get_facts()
            fact_keys = fact_dict.keys()
            fact_keys.sort()
            for key in fact_keys:
                value = fact_dict[key]
                if str(value).strip() == "":
                    value = _("Unknown")
                print "%s: %s" % (key, value)

        if self.options.update:
            facts = inj.require(inj.FACTS)
            try:
                facts.update_check(self.cp, identity.uuid, force=True)
            except connection.RestlibException, re:
                log.exception(re)
                system_exit(os.EX_SOFTWARE, re.msg)
            log.info("Succesfully updated the system facts.")
            print _("Successfully updated the system facts.")


class ImportCertCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Import certificates which were provided outside of the tool")
        super(ImportCertCommand, self).__init__("import", shortdesc, False)

        self.parser.add_option("--certificate", action="append", dest="certificate_file",
                               help=_("certificate file to import (can be specified more than once)"))

    def _validate_options(self):
        if not self.options.certificate_file:
            system_exit(os.EX_USAGE, _("Error: This command requires that you specify a certificate with --certificate."))

    def _do_command(self):
        self._validate_options()
        # Return code
        imported_certs = []
        for src_cert_file in self.options.certificate_file:
            if os.path.exists(src_cert_file):
                try:
                    extractor = managerlib.ImportFileExtractor(src_cert_file)

                    #Verify the entitlement data.
                    if extractor.verify_valid_entitlement():
                        extractor.write_to_disk()
                        print(_("Successfully imported certificate %s") %
                                    os.path.basename(src_cert_file))
                        imported_certs.append(extractor.get_cert())
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

        # update branding info for the imported certs, if needed
        if imported_certs:
            # RHELBrandsInstaller will load ent dir by default
            brands_installer = rhelentbranding.RHELBrandsInstaller()
            brands_installer.install()

        self._request_validity_check()

        return_code = 0
        if not imported_certs:
            return_code = 1

        return return_code

    def require_connection(self):
        return False


class PluginsCommand(CliCommand):
    def __init__(self):
        shortdesc = _("View and configure with 'subscription-manager plugins'")
        super(PluginsCommand, self).__init__("plugins", shortdesc, False)

        self.parser.add_option("--list", action="store_true",
                                help=_("list %s plugins") % SM)
        self.parser.add_option("--listslots", action="store_true",
                                help=_("list %s plugin slots") % SM)
        self.parser.add_option("--listhooks", action="store_true",
                                help=_("list %s plugin hooks") % SM)
        self.parser.add_option("--verbose", action="store_true",
                               default=False,
                               help=_("show verbose plugin info"))

    def _validate_options(self):
        # default to list
        if not (self.options.list or
                self.options.listslots or
                 self.options.listhooks):
            self.options.list = True

    def require_connection(self):
        return False

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

        def repo_callback(option, opt, repoid, parser):
            """
            Store our repos to enable and disable in a combined, ordered list of
            tuples. (enabled, repoid)

            This allows us to have our expected behaviour when we do things like
            --disable="*" --enable="1" --enable="2".
            """
            status = '0'
            if opt == '--enable':
                status = '1'
            vars(parser.values).setdefault('repo_actions',
                []).append((status, repoid))

        def list_callback(option, opt, repoid, parser):
            """
            Handles setting both enabled/disabled filter options when the --list argument is
            provided.

            Allows for --list to perform identically to --list-enabled --list-disabled
            """
            parser.values.list = True

            if opt in ("--list", "--list-enabled"):
                parser.values.list_enabled = True

            if opt in ("--list", "--list-disabled"):
                parser.values.list_disabled = True

        self.parser.add_option("--list",
                               action="callback", callback=list_callback, dest="list", default=False,
                               help=_("list all known repositories for this system"))
        self.parser.add_option("--list-enabled",
                               action="callback", callback=list_callback, dest="list_enabled", default=False,
                               help=_("list known, enabled repositories for this system"))
        self.parser.add_option("--list-disabled",
                               action="callback", callback=list_callback, dest="list_disabled", default=False,
                               help=_("list known, disabled repositories for this system"))
        self.parser.add_option("--enable", dest="enable", type="str",
                               action='callback', callback=repo_callback, metavar="REPOID",
                               help=_("repository to enable (can be specified more than once). Wildcards (* and ?) are supported."))
        self.parser.add_option("--disable", dest="disable", type="str",
                               action='callback', callback=repo_callback, metavar="REPOID",
                               help=_("repository to disable (can be specified more than once). Wildcards (* and ?) are supported."))

    def _validate_options(self):
        if not (self.options.list or hasattr(self.options, 'repo_actions')):
            self.options.list = True
            self.options.list_enabled = True
            self.options.list_disabled = True

    def _do_command(self):
        self._validate_options()
        rc = 0
        if not manage_repos_enabled():
            print _("Repositories disabled by configuration.")
            return rc

        # Pull down any new entitlements and refresh the entitlements directory
        if self.identity.is_valid():
            cert_action_client = ActionClient()
            cert_action_client.update()
            self._request_validity_check()

        self.use_overrides = self.cp.supports_resource('content_overrides')

        # specifically, yum repos, for now.
        rl = RepoActionInvoker()
        repos = rl.get_repos()

        if hasattr(self.options, 'repo_actions'):
            rc = self._set_repo_status(repos, rl, self.options.repo_actions)

        if self.options.list:
            if len(repos):
                # TODO: Perhaps this should be abstracted out as well...?
                def filter_repos(repo):
                    show_enabled = (self.options.list_enabled and repo["enabled"] != '0')
                    show_disabled = (self.options.list_disabled and repo["enabled"] == '0')

                    return show_enabled or show_disabled

                repos = filter(filter_repos, repos)

                if len(repos):
                    print("+----------------------------------------------------------+")
                    print _("    Available Repositories in %s") % rl.get_repo_file()
                    print("+----------------------------------------------------------+")

                    for repo in repos:
                        print columnize(REPOS_LIST, echo_columnize_callback,
                            repo.id,
                            repo["name"],
                            repo["baseurl"],
                            repo["enabled"]) + "\n"
                else:
                    print _("There were no available repositories matching the specified criteria.")
            else:
                print _("This system has no repositories available through subscriptions.")

        return rc

    def _set_repo_status(self, repos, repo_action_invoker, repo_actions):
        """
        Given a list of repo actions (tuple of enable/disable and
        repo ID), build the master list (without duplicates) to send to the
        server.
        """
        rc = 0

        # Maintain a dict of repo to enabled/disabled status. This allows us
        # to remove dupes and send only the last action specified by the user
        # on the command line. Items will be overwritten as we process the CLI
        # arguments in order.
        repos_to_modify = {}

        for (status, repoid) in repo_actions:
            matches = set([repo for repo in repos if fnmatch.fnmatch(repo.id, repoid)])
            if not matches:
                rc = 1
                print _("Error: %s is not a valid repository ID. "
                        "Use --list option to see valid repositories.") % repoid

            # Overwrite repo if it's already in the dict, we want the last
            # match to be the one sent to server.
            for repo in matches:
                repos_to_modify[repo] = status

        if repos_to_modify:
            # The cache should be primed at this point by the
            # repo_action_invoker.get_repos()
            cache = inj.require(inj.OVERRIDE_STATUS_CACHE)

            if self.is_registered() and self.use_overrides:
                overrides = [{'contentLabel': repo.id, 'name': 'enabled', 'value': repos_to_modify[repo]} for repo in repos_to_modify]
                results = self.cp.setContentOverrides(self.identity.uuid, overrides)

                cache = inj.require(inj.OVERRIDE_STATUS_CACHE)

                # Update the cache with the returned JSON
                cache.server_status = results
                cache.write_cache()

                repo_action_invoker.update()
            else:
                # In the disconnected case we must modify the repo file directly.
                changed_repos = [repo for repo in matches if repo['enabled'] != status]
                for repo in changed_repos:
                    repo['enabled'] = status
                if changed_repos:
                    repo_file = RepoFile()
                    repo_file.read()
                    for repo in changed_repos:
                        repo_file.update(repo)
                    repo_file.write()

        for repo in repos_to_modify:
            # Watchout for string comparison here:
            if repos_to_modify[repo] == "1":
                print _("Repository '%s' is enabled for this system.") % repo.id
            else:
                print _("Repository '%s' is disabled for this system.") % repo.id
        return rc


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
                system_exit(os.EX_USAGE, _("Error: --list should not be used with any other options for setting or removing configurations."))

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
                    system_exit(os.EX_USAGE, _("Error: configuration entry designation for removal must be of format [section.name]"))

                section = r.split('.')[0]
                name = r.split('.')[1]
                found = False
                if cfg.has_section(section):
                    for key, value in cfg.items(section):
                        if name == key:
                            found = True
                if not found:
                    system_exit(os.EX_CONFIG, _("Error: Section %s and name %s does not exist.") % (section, name))

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
                    if (value == cfg.get_default(section, name)):
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
                    if not cfg.has_default(section, name):
                        cfg.set(section, name, '')
                        print _("You have removed the value for section %s and name %s.") % (section, name)
                    else:
                        cfg.set(section, name, cfg.get_default(section, name))
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
        self.parser.add_option("--no-overlap", action='store_true',
                               help=_("shows pools which provide products that are not already covered; only used with --available"))
        self.parser.add_option("--match-installed", action="store_true",
                               help=_("shows only subscriptions matching products that are currently installed; only used with --available"))
        self.parser.add_option("--matches", dest="filter_string",
                               help=_("lists only subscriptions or products containing the specified expression in the subscription or product information, varying with the list requested and the server version (case-insensitive)."))
        self.parser.add_option("--pool-only", dest="pid_only", action="store_true",
                               help=_("lists only the pool IDs for applicable available or consumed subscriptions; only used with --available and --consumed"))

    def _validate_options(self):
        if (self.options.all and not self.options.available):
            system_exit(os.EX_USAGE, _("Error: --all is only applicable with --available"))
        if (self.options.on_date and not self.options.available):
            system_exit(os.EX_USAGE, _("Error: --ondate is only applicable with --available"))
        if self.options.service_level is not None and not (self.options.consumed or self.options.available):
            system_exit(os.EX_USAGE, _("Error: --servicelevel is only applicable with --available or --consumed"))
        if not (self.options.available or self.options.consumed):
            self.options.installed = True
        if not self.options.available and self.options.match_installed:
            system_exit(os.EX_USAGE, _("Error: --match-installed is only applicable with --available"))
        if self.options.no_overlap and not self.options.available:
            system_exit(os.EX_USAGE, _("Error: --no-overlap is only applicable with --available"))
        if self.options.pid_only and self.options.installed:
            system_exit(os.EX_USAGE, _("Error: --pool-only is only applicable with --available and/or --consumed"))

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()

        if self.options.installed and not self.options.pid_only:
            iproducts = get_installed_product_status(self.product_dir, self.entitlement_dir, self.cp, self.options.filter_string)

            if len(iproducts):
                print "+-------------------------------------------+"
                print _("    Installed Product Status")
                print "+-------------------------------------------+"

                for product in iproducts:
                    status = STATUS_MAP[product[4]]
                    print columnize(INSTALLED_PRODUCT_STATUS, none_wrap_columnize_callback,
                                product[0], product[1], product[2], product[3],
                                status, product[5], product[6], product[7]) + "\n"
            else:
                if self.options.filter_string:
                    print(_("No installed products were found matching the expression \"%s\".") % self.options.filter_string)
                else:
                    print(_("No installed products to list"))

        if self.options.available:
            self.assert_should_be_registered()
            on_date = None
            if self.options.on_date:
                try:
                    # doing it this ugly way for pre python 2.5
                    on_date = datetime.datetime(
                            *(strptime(self.options.on_date, '%Y-%m-%d')[0:6]))
                except Exception:
                    # Translators: dateexample is current date in format like 2014-11-31
                    msg = _("Date entered is invalid. Date should be in YYYY-MM-DD format (example: {dateexample})")
                    dateexample = strftime("%Y-%m-%d", localtime())
                    system_exit(os.EX_DATAERR,
                                msg.format(dateexample=dateexample))

            facts = inj.require(inj.FACTS)
            epools = managerlib.get_available_entitlements(facts=facts,
                                                           get_all=self.options.all,
                                                           active_on=on_date,
                                                           overlapping=self.options.no_overlap,
                                                           uninstalled=self.options.match_installed,
                                                           filter_string=self.options.filter_string)

            # Filter certs by service level, if specified.
            # Allowing "" here.
            if self.options.service_level is not None:
                epools = self._filter_pool_json_by_service_level(epools, self.options.service_level)

            if len(epools):
                if self.options.pid_only:
                    for data in epools:
                        print data['id']
                else:
                    print("+-------------------------------------------+")
                    print("    " + _("Available Subscriptions"))
                    print("+-------------------------------------------+")

                    for data in epools:
                        if PoolWrapper(data).is_virt_only():
                            machine_type = machine_type = _("Virtual")
                        else:
                            machine_type = _("Physical")

                        if 'management_enabled' in data and data['management_enabled']:
                            data['management_enabled'] = _("Yes")
                        else:
                            data['management_enabled'] = _("No")

                        kwargs = {"filter_string": self.options.filter_string,
                                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                                  "is_atty": sys.stdout.isatty()}
                        print columnize(AVAILABLE_SUBS_LIST, highlight_by_filter_string_columnize_callback,
                                data['productName'],
                                data['providedProducts'],
                                data['productId'],
                                data['contractNumber'] or "",
                                data['id'],
                                data['management_enabled'],
                                data['quantity'],
                                data['suggested'],
                                data['service_level'] or "",
                                data['service_type'] or "",
                                data['pool_type'],
                                data['endDate'],
                                machine_type, **kwargs) + "\n"
            elif not self.options.pid_only:
                if self.options.filter_string and self.options.service_level:
                    print(
                        _("No available subscription pools were found matching the expression \"%s\" and the service level \"%s\".")
                        % (self.options.filter_string, self.options.service_level)
                    )
                elif self.options.filter_string:
                    print(
                        _("No available subscription pools were found matching the expression \"%s\".")
                        % (self.options.filter_string)
                    )
                elif self.options.service_level:
                    print(
                        _("No available subscription pools were found matching the service level \"%s\".")
                        % (self.options.service_level)
                    )
                else:
                    print(_("No available subscription pools to list"))

        if self.options.consumed:
            self.print_consumed(service_level=self.options.service_level, filter_string=self.options.filter_string, pid_only=self.options.pid_only)

    def _filter_pool_json_by_service_level(self, pools, service_level):

        def filter_pool_data_by_service_level(pool_data):
            pool_level = ""
            if pool_data['service_level']:
                pool_level = pool_data['service_level']

            return service_level.lower() == pool_level.lower()

        return filter(filter_pool_data_by_service_level, pools)

    def print_consumed(self, service_level=None, filter_string=None, pid_only=False):
        # list all certificates that have not yet expired, even those
        # that are not yet active.
        certs = self.entitlement_dir.list()
        cert_filter = EntitlementCertificateFilter(filter_string=filter_string, service_level=service_level)

        if len(certs):
            # Check if we need to apply our cert filter
            if service_level is not None or filter_string is not None:
                certs = filter(cert_filter.match, certs)

            # Process and display our (filtered) certs:
            if len(certs):
                if pid_only:
                    for cert in certs:
                        if hasattr(cert.pool, "id"):
                            print cert.pool.id
                else:
                    print("+-------------------------------------------+")
                    print("   " + _("Consumed Subscriptions"))
                    print("+-------------------------------------------+")

                    sorter = inj.require(inj.CERT_SORTER)
                    cert_reasons_map = sorter.reasons.get_subscription_reasons_map()
                    pooltype_cache = inj.require(inj.POOLTYPE_CACHE)

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
                        system_type = ""
                        provides_management = "No"

                        order = cert.order

                        if order:
                            service_level = order.service_level or ""
                            service_type = order.service_type or ""
                            name = order.name
                            sku = order.sku
                            contract = order.contract or ""
                            account = order.account or ""
                            quantity_used = order.quantity_used
                            if order.virt_only:
                                system_type = _("Virtual")
                            else:
                                system_type = _("Physical")

                            if order.provides_management:
                                provides_management = _("Yes")
                            else:
                                provides_management = _("No")

                        pool_id = _("Not Available")
                        if hasattr(cert.pool, "id"):
                            pool_id = cert.pool.id

                        product_names = [p.name for p in cert.products]

                        reasons = []
                        pool_type = ''

                        if inj.require(inj.CERT_SORTER).are_reasons_supported():
                            if cert.subject and 'CN' in cert.subject:
                                if cert.subject['CN'] in cert_reasons_map:
                                    reasons = cert_reasons_map[cert.subject['CN']]
                                pool_type = pooltype_cache.get(pool_id)

                            # 1180400: Status details is empty when GUI is not
                            if not reasons:
                                if cert in sorter.valid_entitlement_certs:
                                    reasons.append(_("Subscription is current"))
                                else:
                                    if cert.valid_range.end() < datetime.datetime.now(GMT()):
                                        reasons.append(_("Subscription is expired"))
                                    else:
                                        reasons.append(_("Subscription has not begun"))
                        else:
                            reasons.append(_("Subscription management service doesn't support Status Details."))

                        kwargs = {"filter_string": filter_string,
                                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                                  "is_atty": sys.stdout.isatty()}
                        print columnize(CONSUMED_LIST, highlight_by_filter_string_columnize_callback,
                            name,
                            product_names,
                            sku,
                            contract,
                            account,
                            cert.serial,
                            pool_id,
                            provides_management,
                            cert.is_valid(),
                            quantity_used,
                            service_level,
                            service_type,
                            reasons,
                            pool_type,
                            managerlib.format_date(cert.valid_range.begin()),
                            managerlib.format_date(cert.valid_range.end()),
                            system_type, **kwargs
                        ) + "\n"
            elif not pid_only:
                if filter_string and service_level:
                    print(
                        _("No consumed subscription pools were found matching the expression \"%s\" and the service level \"%s\".")
                        % (filter_string, service_level)
                    )
                elif filter_string:
                    print(
                        _("No consumed subscription pools were found matching the expression \"%s\".")
                        % (filter_string)
                    )
                elif service_level:
                    print(
                        _("No consumed subscription pools were found matching the service level \"%s\".")
                        % (service_level)
                    )
                else:
                    print(_("No consumed subscription pools were found matching the specified criteria."))
        elif not pid_only:
            print(_("No consumed subscription pools to list"))


class OverrideCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Manage custom content repository settings")
        super(OverrideCommand, self).__init__("repo-override", shortdesc, False)
        self.parser.add_option("--repo", dest="repos", action="append", metavar="REPOID",
            help=_("repository to modify (can be specified more than once)"))
        self.parser.add_option("--remove", dest="removals", action="append", metavar="NAME",
            help=_("name of the override to remove (can be specified more than once); used with --repo option."))
        self.parser.add_option("--add", dest="additions", action="callback", callback=self._colon_split,
            type="string", metavar="NAME:VALUE",
            help=_("name and value of the option to override separated by a colon (can be specified more than once); used with --repo option."))
        self.parser.add_option("--remove-all", action="store_true",
            help=_("remove all overrides; can be specific to a repository by providing --repo"))
        self.parser.add_option("--list", action="store_true",
            help=_("list all overrides; can be specific to a repository by providing --repo"))

    def _colon_split(self, option, opt_str, value, parser):
        if parser.values.additions is None:
            parser.values.additions = {}

        k, colon, v = value.partition(':')
        if not v:
            raise OptionValueError(_("--add arguments should be in the form of \"name:value\""))

        parser.values.additions[k] = v

    def _validate_options(self):
        if self.options.additions or self.options.removals:
            if not self.options.repos:
                system_exit(os.EX_USAGE, _("Error: You must specify a repository to modify"))
            if self.options.remove_all or self.options.list:
                system_exit(os.EX_USAGE, _("Error: You may not use --add or --remove with --remove-all and --list"))
        if self.options.list and self.options.remove_all:
            system_exit(os.EX_USAGE, _("Error: You may not use --list with --remove-all"))
        if self.options.repos and not (self.options.list or self.options.additions or
                                       self.options.removals or self.options.remove_all):
            system_exit(os.EX_USAGE, _("Error: The --repo option must be used with --list or --add or --remove."))
        # If no relevant options were given, just show a list
        if not (self.options.repos or self.options.additions or
                self.options.removals or self.options.remove_all or self.options.list):
            self.options.list = True

    def _do_command(self):
        self._validate_options()
        # Abort if not registered
        self.assert_should_be_registered()

        if not self.cp.supports_resource('content_overrides'):
            system_exit(os.EX_UNAVAILABLE, _("Error: The 'repo-override' command is not supported by the server."))

        # update entitlement certificates if necessary. If we do have new entitlements
        # CertLib.update() will call RepoActionInvoker.update().
        self.entcertlib.update()
        # make sure the EntitlementDirectory singleton is refreshed
        self._request_validity_check()

        overrides = Overrides()

        if not manage_repos_enabled():
            print _("Repositories disabled by configuration.")

        if self.options.list:
            results = overrides.get_overrides(self.identity.uuid)
            if results:
                self._list(results, self.options.repos)
            else:
                print _("This system does not have any content overrides applied to it.")
            return

        if self.options.additions:
            repo_ids = [repo.id for repo in overrides.repo_lib.get_repos(apply_overrides=False)]
            to_add = [Override(repo, name, value) for repo in self.options.repos for name, value in self.options.additions.items()]
            try:
                results = overrides.add_overrides(self.identity.uuid, to_add)
            except connection.RestlibException, ex:
                if ex.code == 400:
                    # black listed overrides specified.
                    # Print message and return a less severe code.
                    system_exit(1, ex)
                else:
                    raise ex

            # Print out warning messages if the specified repo does not exist in the repo file.
            for repo in self.options.repos:
                if repo not in repo_ids:
                    print _("Repository '%s' does not currently exist, but the override has been added.") % repo

        if self.options.removals:
            to_remove = [Override(repo, item) for repo in self.options.repos for item in self.options.removals]
            results = overrides.remove_overrides(self.identity.uuid, to_remove)
        if self.options.remove_all:
            results = overrides.remove_all_overrides(self.identity.uuid, self.options.repos)

        # Update the cache and refresh the repo file.
        overrides.update(results)

    def _list(self, all_overrides, specific_repos):
        overrides = {}
        for override in all_overrides:
            repo = override.repo_id
            name = override.name
            value = override.value
            # overrides is a hash of hashes.  Like this: {'repo_x': {'enabled': '1', 'gpgcheck': '1'}}
            overrides.setdefault(repo, {})[name] = value

        to_show = set(overrides.keys())
        if specific_repos:
            specific_repos = set(specific_repos)
            for r in specific_repos.difference(to_show):
                print _("Nothing is known about '%s'") % r
            # Take the intersection of the sets
            to_show &= specific_repos

        for repo in sorted(to_show):
            print _("Repository: %s") % repo
            repo_data = sorted(overrides[repo].items(), key=lambda x: x[0])
            # Split the list of 2-tuples into a list of names and a list of keys
            names, values = zip(*repo_data)
            names = ["%s:" % x for x in names]
            print columnize(names, echo_columnize_callback, *values, indent=2) + "\n"


class VersionCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Print version information")

        super(VersionCommand, self).__init__("version", shortdesc, False)

    def _do_command(self):
        self.log_server_version()
        print (_("server type: %s") % self.server_versions["server-type"])
        print (_("subscription management server: %s") % self.server_versions["candlepin"])
        print (_("subscription management rules: %s") % self.server_versions["rules-version"])
        print ("subscription-manager: %s" % self.client_versions["subscription-manager"])
        print ("python-rhsm: %s" % self.client_versions["python-rhsm"])


class StatusCommand(CliCommand):

    def __init__(self):
        shortdesc = _("Show status information for this system's subscriptions and products")
        super(StatusCommand, self).__init__("status", shortdesc, True)
        self.parser.add_option("--ondate", dest="on_date",
                                help=(_("future date to check status on, defaults to today's date (example: %s)")
                                      % strftime("%Y-%m-%d", localtime())))

    def _do_command(self):
        # list status and all reasons it is not valid
        if self.options.on_date:
            try:
                # doing it this ugly way for pre python 2.5
                on_date = datetime.datetime(
                        *(strptime(self.options.on_date, '%Y-%m-%d')[0:6]))
                if on_date.date() < datetime.datetime.now().date():
                    system_exit(os.EX_USAGE, _("Past dates are not allowed"))
                self.sorter = ComplianceManager(on_date)
            except Exception:
                system_exit(os.EX_DATAERR, _("Date entered is invalid. Date should be in YYYY-MM-DD format (example: ") + strftime("%Y-%m-%d", localtime()) + " )")
        else:
            self.sorter = inj.require(inj.CERT_SORTER)

        result = 1

        print("+-------------------------------------------+")
        print("   " + _("System Status Details"))
        print("+-------------------------------------------+")

        if self.is_registered():
            overall_status = self.sorter.get_system_status()
            reasons = self.sorter.reasons.get_name_message_map()

            if self.sorter.is_valid():
                result = 0

            print(_("Overall Status: %s\n") % overall_status)

            columns = get_terminal_width()
            for name in reasons:
                print format_name(name + ':', 0, columns)
                for message in reasons[name]:
                    print '- %s' % format_name(message, 2, columns)
                print ''
        else:
            print(_("Overall Status: %s\n") % _("Unknown"))

        return result


class ManagerCLI(CLI):

    def __init__(self):
        commands = [RegisterCommand, UnRegisterCommand, ConfigCommand, ListCommand,
                    SubscribeCommand, UnSubscribeCommand, FactsCommand,
                    IdentityCommand, OwnersCommand, RefreshCommand, CleanCommand,
                    RedeemCommand, ReposCommand, ReleaseCommand, StatusCommand,
                    EnvironmentsCommand, ImportCertCommand, ServiceLevelCommand,
                    VersionCommand, RemoveCommand, AttachCommand, PluginsCommand,
                    AutohealCommand, OverrideCommand]
        CLI.__init__(self, command_classes=commands)

    def main(self):
        managerlib.check_identity_cert_perms()
        return CLI.main(self)


if __name__ == "__main__":
    ManagerCLI().main()
