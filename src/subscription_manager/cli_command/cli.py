#
# Subscription manager command line utility.
#
# Copyright (c) 2021 Red Hat, Inc.
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
import logging
import os
import socket
import sys

import rhsm.config
import rhsm.connection as connection
import subscription_manager.injection as inj

from rhsm.certificate import CertificateException
from rhsm.connection import ProxyException
from rhsm.https import ssl
from rhsm.utils import ServerUrlParseError, remove_scheme

from rhsmlib.services import config

from subscription_manager.cli import AbstractCLICommand, InvalidCLIOptionError, system_exit
from subscription_manager.entcertlib import EntCertActionInvoker
from subscription_manager.exceptions import ExceptionMapper
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import generate_correlation_id, get_client_versions, get_server_versions, \
    parse_server_info, parse_baseurl_info, format_baseurl, is_valid_server_info, MissingCaCertException, \
    get_current_owner

ERR_NOT_REGISTERED_MSG = _(
    "This system is not yet registered. Try 'subscription-manager register --help' for more information.")
ERR_NOT_REGISTERED_CODE = 1

log = logging.getLogger(__name__)
conf = config.Config(rhsm.config.get_config_parser())


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
        self.no_proxy = None

        self.entitlement_dir = inj.require(inj.ENT_DIR)
        self.product_dir = inj.require(inj.PROD_DIR)

        self.client_versions = self._default_client_version()
        self.server_versions = self._default_server_version()

        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)

        self.identity = inj.require(inj.IDENTITY)

        self.correlation_id = generate_correlation_id()

    def _print_ignore_auto_attach_message(self):
        """
        This message is shared by attach command and register command, because
        both commands can do auto-attach.
        :return: None
        """
        owner = get_current_owner(self.cp, self.identity)
        # We displayed Owner name: `owner_name = owner['displayName']`, but such behavior
        # was not consistent with rest of subscription-manager
        # Look at this comment: https://bugzilla.redhat.com/show_bug.cgi?id=1826300#c8
        owner_id = owner['key']
        print(
            _(
                'Ignoring request to auto-attach. '
                'It is disabled for org "{owner_id}" because of the content access mode setting.'
            ).format(owner_id=owner_id)
        )

    def _get_logger(self):
        return logging.getLogger("rhsm-app.{module}.{name}".format(module=self.__module__, name=self.__class__.__name__))

    def test_proxy_connection(self):
        if not self.proxy_hostname and not conf["server"]["proxy_hostname"]:
            return True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            result = s.connect_ex((
                self.proxy_hostname or conf["server"]["proxy_hostname"],
                int(self.proxy_port or conf["server"]["proxy_port"] or rhsm.config.DEFAULT_PROXY_PORT)
            ))
        except Exception as e:
            log.error("Attempted bad proxy: {e}".format(e=e))
            return False
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
        self.parser.add_argument("--serverurl", dest="server_url",
                               default=None, help=_("server URL in the form of https://hostname:port/prefix"))
        self.parser.add_argument("--insecure", action="store_true",
                                default=False, help=_("do not check the entitlement server SSL certificate against "
                                                      "available certificate authorities"))

    def _add_proxy_options(self):
        """ Add proxy options that apply to sub-commands that require network connections. """
        self.parser.add_argument("--proxy", dest="proxy_url",
                               default=None, help=_("proxy URL in the form of proxy_hostname:proxy_port"))
        self.parser.add_argument("--proxyuser", dest="proxy_user",
                                default=None, help=_("user for HTTP proxy with basic authentication"))
        self.parser.add_argument("--proxypassword", dest="proxy_password",
                                default=None, help=_("password for HTTP proxy with basic authentication"))
        self.parser.add_argument('--noproxy', dest='no_proxy',
                               default=None, help=_("host suffixes that should bypass HTTP proxy"))

    def _do_command(self):
        pass

    def assert_should_be_registered(self):
        if not self.is_consumer_cert_present():
            system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)
        elif not self.is_registered():
            system_exit(os.EX_DATAERR, _(
                "Consumer identity either does not exist or is corrupted. Try register --help"
            ))

    def is_consumer_cert_present(self):
        self.identity = inj.require(inj.IDENTITY)
        return self.identity.is_present()

    def is_registered(self):
        self.identity = inj.require(inj.IDENTITY)
        log.debug("{identity}".format(identity=self.identity))
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
        return {"subscription-manager": _("Unknown")}

    def _default_server_version(self):
        return {"candlepin": _("Unknown"),
                "rules-type": _("Unknown"),
                "server-type": _("Unknown")}

    def log_client_version(self):
        self.client_versions = get_client_versions()
        log.debug("Client Versions: {versions}".format(versions=self.client_versions))

    def log_server_version(self):
        # can't check the server version without a connection
        # and valid registration
        if not self.require_connection():
            return

        # get_server_versions needs to handle any exceptions
        # and return the server dict
        self.server_versions = get_server_versions(self.no_auth_cp, exception_on_timeout=False)
        log.debug("Server Versions: {versions}".format(versions=self.server_versions))

    def main(self, args=None):

        # TODO: For now, we disable the CLI entirely. We may want to allow some commands in the future.
        if rhsm.config.in_container():
            system_exit(os.EX_CONFIG, _("subscription-manager is disabled when running inside a container. Please refer to your host system for subscription management.\n"))

        config_changed = False

        # In testing we sometimes specify args, otherwise use the default:
        if not args:
            args = sys.argv[1:]

        (self.options, self.args) = self.parser.parse_known_args(args)

        # we dont need argv[0] in this list...
        self.args = self.args[1:]
        # check for unparsed arguments
        if self.args:
            for arg in self.args:
                print(_("cannot parse argument: {}").format(arg))
            system_exit(os.EX_USAGE)

        if hasattr(self.options, "insecure") and self.options.insecure:
            conf["server"]["insecure"] = "1"
            config_changed = True

        if hasattr(self.options, "server_url") and self.options.server_url:
            try:
                (self.server_hostname,
                 self.server_port,
                 self.server_prefix) = parse_server_info(self.options.server_url, conf)
            except ServerUrlParseError as e:
                print(_("Error parsing serverurl:"))
                handle_exception("Error parsing serverurl:", e)

            conf["server"]["hostname"] = self.server_hostname
            conf["server"]["port"] = self.server_port
            conf["server"]["prefix"] = self.server_prefix
            if self.server_port:
                self.server_port = int(self.server_port)
            config_changed = True

        if hasattr(self.options, "base_url") and self.options.base_url:
            try:
                (baseurl_server_hostname,
                 baseurl_server_port,
                 baseurl_server_prefix) = parse_baseurl_info(self.options.base_url)
            except ServerUrlParseError as e:
                print(_("Error parsing baseurl:"))
                handle_exception("Error parsing baseurl:", e)

            conf["rhsm"]["baseurl"] = format_baseurl(
                baseurl_server_hostname,
                baseurl_server_port,
                baseurl_server_prefix)
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
                self.proxy_port = conf['server'].get_int('proxy_port') or rhsm.config.DEFAULT_PROXY_PORT
            config_changed = True

        if hasattr(self.options, "proxy_user") and self.options.proxy_user:
            self.proxy_user = self.options.proxy_user
        if hasattr(self.options, "proxy_password") and self.options.proxy_password:
            self.proxy_password = self.options.proxy_password
        if hasattr(self.options, "no_proxy") and self.options.no_proxy:
            self.no_proxy = self.options.no_proxy

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
        if self.no_proxy:
            connection_info['no_proxy_arg'] = self.no_proxy

        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.cp_provider.set_connection_info(**connection_info)
        self.log.debug("X-Correlation-ID: {id}".format(id=self.correlation_id))
        self.cp_provider.set_correlation_id(self.correlation_id)

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
                try:
                    # catch host/port issues; does not catch auth issues
                    if not self.test_proxy_connection():
                        system_exit(os.EX_UNAVAILABLE, _("Proxy connection failed, please check your settings."))

                    # this tries to actually connect to the server and ping it
                    if not is_valid_server_info(self.no_auth_cp):
                        system_exit(os.EX_UNAVAILABLE, _("Unable to reach the server at {host}:{port}{handler}").format(
                            host=self.no_auth_cp.host,
                            port=self.no_auth_cp.ssl_port,
                            handler=self.no_auth_cp.handler
                        ))

                except MissingCaCertException:
                    system_exit(os.EX_CONFIG,
                                _("Error: CA certificate for subscription service has not been installed."))
                except ProxyException:
                    system_exit(os.EX_UNAVAILABLE, _("Proxy connection failed, please check your settings."))

        else:
            self.cp = None

        # do the work, catch most common errors here:
        try:

            return_code = self._do_command()

            # Only persist the config changes if there was no exception
            if config_changed and self.persist_server_options():
                conf.persist()

            if return_code is not None:
                return return_code
        except (CertificateException, ssl.SSLError) as e:
            log.error(e)
            system_exit(os.EX_SOFTWARE, _('System certificates corrupted. Please reregister.'))
        except connection.GoneException as ge:
            if ge.deleted_id == self.identity.uuid:
                log.critical("Consumer profile \"{uuid}\" has been deleted from the server.".format(uuid=self.identity.uuid))
                system_exit(os.EX_UNAVAILABLE, _("Consumer profile \"{uuid}\" has been deleted from the server. You can use command clean or unregister to remove local profile.").format(uuid=self.identity.uuid))
            else:
                raise ge
        except InvalidCLIOptionError as err:
            # This exception is handled in cli module
            raise err
        except Exception as err:
            handle_exception("exception caught in subscription-manager", err)
