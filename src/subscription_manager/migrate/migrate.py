from __future__ import print_function, division, absolute_import

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
import getpass
import libxml2
import logging
import os
import re
import readline
import shutil
import six.moves
import subprocess
import sys

from datetime import datetime
from rhsm.https import ssl

from rhn import rpclib

from rhsm.connection import RemoteServerException, RestlibException
from rhsm.utils import ServerUrlParseError

from subscription_manager.i18n import ugettext as _

from subscription_manager import injection as inj
from subscription_manager.cli import system_exit
from subscription_manager.i18n_optparse import OptionParser, \
        USAGE, WrappedIndentedHelpFormatter
from subscription_manager.productid import ProductDatabase
from subscription_manager import repolib
from rhsm.utils import parse_url
from rhsm import ourjson as json

from rhsm.config import initConfig
from rhsmlib.services import config

_RHNLIBPATH = "/usr/share/rhn"
if _RHNLIBPATH not in sys.path:
    sys.path.append(_RHNLIBPATH)

_UP2DATE_CLIENT_CONFIG_ERROR = _("Could not find up2date_client.config module! "
                                 "Perhaps this script was already executed with --remove-rhn-packages?")
_UP2DATE_CLIENT_RHNCHANNEL_ERROR = _("Could not find up2date_client.config module! "
                                     "Perhaps this script was already executed with --remove-rhn-packages?")

# Don't raise ImportErrors so we can run the unit tests on Fedora.
try:
    from up2date_client.config import initUp2dateConfig
except ImportError:
    def initUp2dateConfig():
        raise NotImplementedError(_UP2DATE_CLIENT_CONFIG_ERROR)

try:
    from up2date_client.rhnChannel import getChannels
except ImportError:
    def getChannels():
        raise NotImplementedError(_UP2DATE_CLIENT_RHNCHANNEL_ERROR)

log = logging.getLogger(__name__)

SEE_LOG_FILE = _(u"See /var/log/rhsm/rhsm.log for more details.")

CONNECTION_FAILURE = _(u"Unable to connect to certificate server: %s.  ") + SEE_LOG_FILE

FACT_FILE = "/etc/rhsm/facts/migration.facts"

YUM_PLUGIN_CONF = '/etc/yum/pluginconf.d/rhnplugin.conf'

DOUBLE_MAPPED = "rhel-.*?-(client|server)-dts-(5|6)-beta(-debuginfo)?"
# The (?!-beta) bit is a negative lookahead assertion.  So we won't match
# if the 5 or 6 is followed by the word "-beta"
SINGLE_MAPPED = "rhel-.*?-(client|server)-dts-(5|6)(?!-beta)(-debuginfo)?"

LEGACY_DAEMONS = ["osad", "rhnsd"]

LEGACY_PACKAGES = [
    "osad",
    "rhn-check",
    "rhn-client-tools",  # provides up2date_client which means this script won't work after uninstalled
    "rhncfg",
    "rhncfg-actions",
    "rhncfg-client",
    "rhncfg-management",
    "rhn-setup",
    "rhnpush",
    "rhnsd",
    "spacewalk-abrt",
    "spacewalk-oscap",
    "yum-rhn-plugin"
]


class InvalidChoiceError(Exception):
    pass


class Menu(object):
    def __init__(self, choices, header):
        # choices is a tuple with the first value being the display string
        # and the second value being the value to return.
        self.choices = choices
        self.header = header

    def choose(self):
        while True:
            self.display()
            selection = six.moves.input("? ").strip()
            readline.clear_history()
            try:
                return self._get_item(selection)
            except InvalidChoiceError:
                self.display_invalid()

    def display(self):
        print(self.header)
        for index, entry in enumerate(self.choices):
            print("%s. %s" % (index + 1, entry[0]))

    def display_invalid(self):
        print(_("You have entered an invalid choice.  Enter a choice from the menu above."))

    def _get_item(self, selection):
        try:
            index = int(selection) - 1
            # In case some joker enters zero or a negative number
            if index < 0:
                raise InvalidChoiceError
        except TypeError:
            raise InvalidChoiceError
        except ValueError:
            raise InvalidChoiceError

        try:
            return self.choices[index][1]
        except IndexError:
            raise InvalidChoiceError


class UserCredentials(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password


class MigrationEngine(object):
    def __init__(self, options):
        self.rhncfg = initUp2dateConfig()
        self.rhsmcfg = config.Config(initConfig())

        # Sometimes we need to send up the entire contents of the system id file
        # which is referred to in Satellite 5 nomenclature as a "certificate"
        # although it is not an X509 certificate.
        try:
            self.system_id_contents = open(self.rhncfg["systemIdPath"], 'r').read()
        except IOError:
            system_exit(os.EX_IOERR, _("Could not read legacy system id at %s") % self.rhncfg["systemIdPath"])

        self.system_id = self.get_system_id(self.system_id_contents)

        self.proxy_host = None
        self.proxy_port = None
        self.proxy_user = None
        self.proxy_pass = None

        self.cp = None
        self.db = ProductDatabase()

        self.consumer_id = None

        self.options = options
        self.is_hosted = is_hosted()

    def authenticate(self, username, password, user_prompt, pw_prompt):
        if not username:
            username = six.moves.input(user_prompt).strip()
            readline.clear_history()

        if not password:
            password = getpass.getpass(prompt=pw_prompt)

        return UserCredentials(username, password)

    def get_auth(self):
        if self.options.registration_state == "keep":
            self.legacy_creds = UserCredentials(None, None)
        else:
            self.legacy_creds = self.authenticate(self.options.legacy_user, self.options.legacy_password,
                _("Legacy username: "), _("Legacy password: "))

        if self.options.activation_keys:
            self.destination_creds = UserCredentials(None, None)
        elif not self.is_hosted or self.options.destination_url or self.options.registration_state == "keep":
            self.destination_creds = self.authenticate(self.options.destination_user, self.options.destination_password,
                _("Destination username: "), _("Destination password: "))
        else:
            self.destination_creds = self.legacy_creds   # make them the same

    def transfer_http_proxy_settings(self):
        if self.rhncfg['enableProxy']:
            http_proxy = self.rhncfg['httpProxy']
            if http_proxy[:7] == "http://":
                http_proxy = http_proxy[7:]
            try:
                self.proxy_host, self.proxy_port = http_proxy.split(':')
            except ValueError as e:
                log.exception(e)
                system_exit(os.EX_CONFIG, _("Could not read legacy proxy settings.  ") + SEE_LOG_FILE)

            if self.rhncfg['enableProxyAuth']:
                self.proxy_user = self.rhncfg['proxyUser']
                self.proxy_pass = self.rhncfg['proxyPassword']

            log.debug("Using proxy %s:%s" % (self.proxy_host, self.proxy_port))
            if self.options.noproxy:
                # If the user doesn't want to use a proxy to connect to their subscription
                # management server, then remove any proxy information that may have crept in.
                self.rhsmcfg['server']['proxy_hostname'] = ''
                self.rhsmcfg['server']['proxy_port'] = ''
                self.rhsmcfg['server']['proxy_user'] = ''
                self.rhsmcfg['server']['proxy_password'] = ''
            else:
                self.rhsmcfg['server']['proxy_hostname'] = self.proxy_host
                self.rhsmcfg['server']['proxy_port'] = self.proxy_port
                self.rhsmcfg['server']['proxy_user'] = self.proxy_user or ''
                self.rhsmcfg['server']['proxy_password'] = self.proxy_pass or ''
            self.rhsmcfg.persist()

    def _get_connection_info(self):
        url_parse_error = os.EX_USAGE
        try:
            if self.options.destination_url is None:
                url_parse_error = os.EX_CONFIG
                hostname = self.rhsmcfg['server']['hostname']
                port = self.rhsmcfg['server'].get_int('port')
                prefix = self.rhsmcfg['server']['prefix']
            else:
                (_user, _password, hostname, port, prefix) = parse_url(self.options.destination_url, default_port=443)
        except ServerUrlParseError as e:
            system_exit(url_parse_error, _("Error parsing server URL: %s") % e.msg)

        connection_info = {'host': hostname, 'ssl_port': int(port), 'handler': prefix}

        if not self.options.noproxy:
            connection_info['proxy_hostname_arg'] = self.proxy_host
            connection_info['proxy_port_arg'] = self.proxy_port and int(self.proxy_port)
            connection_info['proxy_user_arg'] = self.proxy_user
            connection_info['proxy_password_arg'] = self.proxy_pass

        return connection_info

    def get_candlepin_connection(self, username, password):
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        connection_info = self._get_connection_info()
        self.cp_provider.set_connection_info(**connection_info)

        if username and password:
            self.cp_provider.set_user_pass(username, password)
            return self.cp_provider.get_basic_auth_cp()

        return self.cp_provider.get_no_auth_cp()

    def check_ok_to_proceed(self):
        # check if this machine is already registered to Certicate-based RHN
        identity = inj.require(inj.IDENTITY)
        if identity.is_valid():
            if self.options.five_to_six:
                msgs = [_("This system appears to already be registered to Satellite 6.")]
            else:
                msgs = [_("This system appears to already be registered to Red Hat Subscription Management.")]
                msgs.append(_("Please visit https://access.redhat.com/management/consumers/%s to view the profile details.") % identity.uuid)
            system_exit(1, msgs)

        try:
            self.cp.getStatus()
        except ssl.SSLError as e:
            print(_("The CA certificate for the destination server has not been installed."))
            system_exit(os.EX_SOFTWARE, CONNECTION_FAILURE % e)
        except Exception as e:
            log.exception(e)
            system_exit(os.EX_SOFTWARE, CONNECTION_FAILURE % e)

    def get_org(self, username):
        try:
            owner_list = self.cp.getOwnerList(username)
        except Exception as e:
            log.exception(e)
            system_exit(os.EX_SOFTWARE, CONNECTION_FAILURE % e)

        if len(owner_list) == 0:
            system_exit(1, _("%s cannot register with any organizations.") % username)
        else:
            if self.options.org:
                org_input = self.options.org
            elif len(owner_list) == 1:
                org_input = owner_list[0]['key']
            else:
                org_input = six.moves.input(_("Org: ")).strip()
                readline.clear_history()

            org = None
            for owner_data in owner_list:
                if owner_data['key'] == org_input or owner_data['displayName'] == org_input:
                    org = owner_data['key']
                    break
            if not org:
                system_exit(os.EX_DATAERR, _("Couldn't find organization '%s'.") % org_input)
        return org

    def get_environment(self, owner_key):
        environment_list = []
        try:
            if self.cp.supports_resource('environments'):
                environment_list = self.cp.getEnvironmentList(owner_key)
            elif self.options.environment:
                system_exit(os.EX_UNAVAILABLE, _("Environments are not supported by this server."))
        except Exception as e:
            log.exception(e)
            system_exit(os.EX_SOFTWARE, CONNECTION_FAILURE % e)

        environment = None
        if len(environment_list) > 0:
            if self.options.environment:
                env_input = self.options.environment
            elif len(environment_list) == 1:
                env_input = environment_list[0]['name']
            else:
                env_input = six.moves.input(_("Environment: ")).strip()
                readline.clear_history()

            for env_data in environment_list:
                # See BZ #978001
                if (env_data['name'] == env_input or
                   ('label' in env_data and env_data['label'] == env_input) or
                   ('displayName' in env_data and env_data['displayName'] == env_input)):
                    environment = env_data['name']
                    break
            if not environment:
                system_exit(os.EX_DATAERR, _("Couldn't find environment '%s'.") % env_input)

        return environment

    def connect_to_rhn(self, credentials):
        hostname = self.rhncfg['serverURL'].split('/')[2]
        server_url = 'https://%s/rpc/api' % (hostname)

        try:
            if self.rhncfg['enableProxy']:
                proxy = "%s:%s" % (self.proxy_host, self.proxy_port)
                log.debug("Using proxy %s for legacy API methods" % (proxy))
                if self.rhncfg['enableProxyAuth']:
                    proxy = "@".join(["%s:%s" % (self.proxy_user, self.proxy_pass), proxy])
            else:
                proxy = None

            rpc_session = rpclib.Server(server_url, proxy=proxy)

            ca = self.rhncfg["sslCACert"]
            rpc_session.add_trusted_cert(ca)

            if credentials.username and credentials.password:
                session_key = rpc_session.auth.login(credentials.username, credentials.password)
            else:
                session_key = None

            return (rpc_session, session_key)
        except Exception as e:
            log.exception(e)
            system_exit(1, _("Unable to authenticate to legacy server.  ") + SEE_LOG_FILE)

    def check_has_access(self, rpc_session, session_key):
        try:
            if session_key is None:
                # We should not ever be here.  This method has a guard that keeps it from being
                # called when not needed.  If we see this error, someone has made a programming
                # mistake.
                raise Exception("No session key available.  Check that XMLRPC connection is being made with credentials.")

            rpc_session.system.getDetails(session_key, self.system_id)
        except Exception as e:
            log.exception(e)
            system_exit(1, _("You do not have access to system %s.  ") % self.system_id + SEE_LOG_FILE)

    def resolve_base_channel(self, label, rpc_session, session_key):
        try:
            details = rpc_session.channel.software.getDetails(session_key, label)
        except Exception as e:
            log.exception(e)
            system_exit(os.EX_SOFTWARE, _("Problem encountered getting the list of subscribed channels.  ") + SEE_LOG_FILE)
        if details['clone_original']:
            return self.resolve_base_channel(details['clone_original'], rpc_session, session_key)
        return details

    def get_subscribed_channels_list(self, rpc_session, session_key):
        try:
            channels = getChannels().channels()
        except Exception as e:
            log.exception(e)
            system_exit(os.EX_SOFTWARE, _("Problem encountered getting the list of subscribed channels.  ") + SEE_LOG_FILE)
        if self.options.five_to_six:
            channels = [self.resolve_base_channel(c['label'], rpc_session, session_key) for c in channels]
        return [x['label'] for x in channels]

    def print_banner(self, msg):
        print("\n+-----------------------------------------------------+")
        print(msg)
        print("+-----------------------------------------------------+")

    def check_for_conflicting_channels(self, subscribed_channels):
        jboss_channel = False
        for channel in subscribed_channels:
            if channel.startswith("jbappplatform"):
                if jboss_channel:
                    system_exit(1, _("You are subscribed to more than one jbappplatform channel."
                                    "  This script does not support that configuration."))
                jboss_channel = True

    def get_release(self):
        f = open('/etc/redhat-release')
        lines = f.readlines()
        f.close()
        try:
            major_version = re.search("[0-9]+(?=\.[0-9]+)*", str(lines)).group(0)
        except AttributeError:
            log.error("Could not determine RHEL release from /etc/redhat-release")
            # Leaving no message to stdout/stderr as it's past string freeze
            system_exit(1, "")
        else:
            release = "RHEL-" + major_version
        return release

    def read_channel_cert_mapping(self, mappingfile):
        f = open(mappingfile)
        lines = f.readlines()
        dic_data = {}
        for line in lines:
            # Lines should be of the format
            # key: value
            # Lines beginning with non-letters will be ignored
            if re.match("^[a-zA-Z]", line):
                line = line.replace("\n", "")
                key, val = line.strip().split(": ")
                dic_data[key] = val
        return dic_data

    def handle_collisions(self, applicable_certs):
        # if we have the same product IDs mapping to multiple certificates, we must abort.
        collisions = dict((prod_id, mappings) for prod_id, mappings in list(applicable_certs.items()) if len(mappings) > 1)
        if not collisions:
            return

        log.error("Aborting. Detected the following product ID collisions: %s", collisions)
        self.print_banner(_("Unable to continue migration!"))
        print(_("You are subscribed to channels that have conflicting product certificates."))
        for prod_id, mappings in list(collisions.items()):
            # Flatten the list of lists
            colliding_channels = [item for sublist in list(mappings.values()) for item in sublist]
            print(_("The following channels map to product ID %s:") % prod_id)
            for c in sorted(colliding_channels):
                print("\t%s" % c)
        print(_("Reduce the number of channels per product ID to 1 and run migration again."))
        print(_("To remove a channel, use 'rhn-channel --remove --channel=<conflicting_channel>'."))
        sys.exit(1)

    def deploy_prod_certificates(self, subscribed_channels):
        release = self.get_release()
        mappingfile = "/usr/share/rhsm/product/" + release + "/channel-cert-mapping.txt"
        log.debug("Using mapping file %s", mappingfile)

        try:
            dic_data = self.read_channel_cert_mapping(mappingfile)
        except IOError as e:
            log.exception(e)
            system_exit(os.EX_CONFIG, _("Unable to read mapping file: %(mappingfile)s.\n"
                "Please check that you have the %(package)s package installed.") % {
                    "mappingfile": mappingfile,
                    "package": "subscription-manager-migration-data"})

        applicable_certs = {}
        valid_rhsm_channels = []
        invalid_rhsm_channels = []
        unrecognized_channels = []

        for channel in subscribed_channels:
            try:
                if dic_data[channel] != 'none':
                    valid_rhsm_channels.append(channel)
                    cert = dic_data[channel]
                    log.debug("Mapping found for: %s = %s", channel, cert)
                    prod_id = cert.split('-')[-1].split('.pem')[0]
                    cert_to_channels = applicable_certs.setdefault(prod_id, {})
                    cert_to_channels.setdefault(cert, []).append(channel)
                else:
                    invalid_rhsm_channels.append(channel)
                    log.warn("%s is not mapped to any certificates", channel)
            except Exception:
                unrecognized_channels.append(channel)

        if invalid_rhsm_channels:
            self.print_banner(_("Channels not available on %s:") % self.options.destination_url)
            for i in invalid_rhsm_channels:
                print(i)

        if unrecognized_channels:
            self.print_banner(_("No product certificates are mapped to these legacy channels:"))
            for i in unrecognized_channels:
                print(i)

        if unrecognized_channels or invalid_rhsm_channels:
            if not self.options.force:
                system_exit(1, _("\nUse --force to ignore these channels and continue the migration.\n"))

        # At this point applicable_certs looks something like this
        # { '1': { 'cert-a-1.pem': ['channel1', 'channel2'], 'cert-b-1.pem': ['channel3'] } }
        # This is telling us that product ID 1 maps to two certificates, cert-a and cert-b.
        # Two channels map to the cert-a certificate and one channel maps to cert-b.
        # If we wind up in a situation where a user has channels that map to two different
        # certificates with the same product ID, (e.g. len(hash[product_id]) > 1) we've got a
        # collision and must abort.
        self.handle_collisions(applicable_certs)

        log.debug("Certs to be installed: %s", applicable_certs)

        self.print_banner(_("Installing product certificates for these legacy channels:"))
        for i in valid_rhsm_channels:
            print(i)

        release = self.get_release()

        # creates the product directory if it doesn't already exist
        product_dir = inj.require(inj.PROD_DIR)
        db_modified = False
        for cert_to_channels in list(applicable_certs.values()):
            # At this point handle_collisions should have verified that len(cert_to_channels) == 1
            cert, channels = list(cert_to_channels.items())[0]
            source_path = os.path.join("/usr/share/rhsm/product", release, cert)
            truncated_cert_name = cert.split('-')[-1]
            destination_path = os.path.join(product_dir.path, truncated_cert_name)
            log.debug("Copying %s to %s ", source_path, destination_path)
            shutil.copy2(source_path, destination_path)

            # See BZ #972883. Add an entry to the repo db telling subscription-manager
            # that packages for this product were installed by the RHN repo which
            # conveniently uses the channel name for the repo name.
            db_id = truncated_cert_name.split('.pem')[0]
            for chan in channels:
                self.db.add(db_id, chan)
                db_modified = True

        if db_modified:
            self.db.write()
        print(_("\nProduct certificates installed successfully to %s.") % product_dir.path)

    def clean_up(self, subscribed_channels):
        # Hack to address BZ 853233
        product_dir = inj.require(inj.PROD_DIR)
        if os.path.isfile(os.path.join(product_dir.path, "68.pem")) and \
            os.path.isfile(os.path.join(product_dir.path, "71.pem")):
            try:
                os.remove(os.path.join(product_dir.path, "68.pem"))
                self.db.delete("68")
                self.db.write()
                log.info("Removed 68.pem due to existence of 71.pem")
            except OSError as e:
                log.error(e)

        # Hack to address double mapping for 180.pem and 17{6|8}.pem
        is_double_mapped = [x for x in subscribed_channels if re.match(DOUBLE_MAPPED, x)]
        is_single_mapped = [x for x in subscribed_channels if re.match(SINGLE_MAPPED, x)]

        if is_double_mapped and is_single_mapped:
            try:
                os.remove(os.path.join(product_dir.path, "180.pem"))
                self.db.delete("180")
                self.db.write()
                log.info("Removed 180.pem")
            except OSError as e:
                log.error(e)

    def get_system_id(self, content):
        p = libxml2.parseDoc(content)
        system_id = int(p.xpathEval('string(//member[* = "system_id"]/value/string)').split('-')[1])
        return system_id

    def write_migration_facts(self):
        migration_date = datetime.now().isoformat()

        if not os.path.exists(FACT_FILE):
            f = open(FACT_FILE, 'w')
            json.dump({"migration.classic_system_id": self.system_id,
                       "migration.migrated_from": self.rhncfg['serverURL'],
                       "migration.migration_date": migration_date}, f)
            f.close()

    def disable_yum_rhn_plugin(self):
        # 'Inspired by' up2date_client/rhnreg.py
        """
        Disable yum-rhn-plugin by setting enabled=0 in file
        /etc/yum/pluginconf.d/rhnplugin.conf
        Can thrown IOError exception.
        """
        log.info("Disabling rhnplugin.conf")
        f = open(YUM_PLUGIN_CONF, 'r')
        lines = f.readlines()
        f.close()
        main_section = False
        f = open(YUM_PLUGIN_CONF, 'w')
        for line in lines:
            if re.match("^\[.*]", line):
                if re.match("^\[main]", line):
                    main_section = True
                else:
                    main_section = False
            if main_section:
                line = re.sub('^(\s*)enabled\s*=.+', r'\1enabled = 0', line)
            f.write(line)
        f.close()

    def legacy_unentitle(self, rpc_session):
        try:
            rpc_session.system.unentitle(self.system_id_contents)
        except Exception as e:
            log.exception("Could not remove system entitlement on Satellite 5.", e)
            system_exit(os.EX_SOFTWARE, _("Could not remove system entitlement on legacy server.  ") + SEE_LOG_FILE)
        try:
            self.disable_yum_rhn_plugin()
        except Exception:
            pass

    def legacy_purge(self, rpc_session, session_key):
        system_id_path = self.rhncfg["systemIdPath"]

        log.info("Deleting system %s from legacy server...", self.system_id)
        try:
            result = rpc_session.system.deleteSystems(session_key, self.system_id)
        except Exception:
            log.exception("Could not delete system %s from legacy server" % self.system_id)
            # If we time out or get a network error, log it and keep going.
            shutil.move(system_id_path, system_id_path + ".save")
            print(_("Did not receive a completed unregistration message from legacy server for system %s.") % self.system_id)

            if self.is_hosted:
                print(_("Please investigate on the Customer Portal at https://access.redhat.com."))
            return

        if result:
            log.debug("System %s deleted.  Removing system id file and disabling rhnplugin.conf", self.system_id)
            os.remove(system_id_path)
            try:
                self.disable_yum_rhn_plugin()
            except Exception:
                pass
            print(_("System successfully unregistered from legacy server."))
        else:
            # If the legacy server reports that deletion just failed, then quit.
            system_exit(1, _("Unable to unregister system from legacy server.  ") + SEE_LOG_FILE)

    def load_transition_data(self, rpc_session):
        try:
            transition_data = rpc_session.system.transitionDataForSystem(self.system_id_contents)
            self.consumer_id = transition_data['uuid']
        except Exception as e:
            log.exception(e)
            system_exit(1, _("Could not retrieve system migration data from legacy server.  ") + SEE_LOG_FILE)

    def consumer_exists(self, consumer_id):
        try:
            self.cp.getConsumer(consumer_id)
            return True
        except Exception as e:
            log.exception(e)
            print(_("Consumer %s doesn't exist.  Creating new consumer.") % consumer_id)
            return False

    def register(self, credentials, org, environment):
        # For registering the machine, use the CLI tool to reuse the username/password (because the GUI will prompt for them again)
        # Prepended a \n so translation can proceed without hitch
        print ("")
        print(_("Attempting to register system to destination server..."))
        cmd = ['subscription-manager', 'register']

        # Candlepin doesn't want user credentials with activation keys
        # Auto-attach and environments are also forbidden
        if self.options.activation_keys:
            for key in self.options.activation_keys:
                cmd.append('--activationkey=' + key)
        else:
            cmd.append('--username=' + credentials.username)
            cmd.append('--password=' + credentials.password)

            if environment:
                cmd.append('--environment=' + environment)

            if self.options.auto:
                cmd.append('--auto-attach')

        if self.options.destination_url:
            cmd.append('--serverurl=' + self.options.destination_url)

        if org:
            cmd.append('--org=' + org)

        if self.options.five_to_six:
            if self.consumer_exists(self.consumer_id):
                cmd.append('--consumerid=' + self.consumer_id)

        if self.options.service_level:
            servicelevel = self.select_service_level(org, self.options.service_level)
            cmd.append('--servicelevel=' + servicelevel)

        subprocess.call(cmd)

        identity = inj.require(inj.IDENTITY)
        identity.reload()

        if not identity.is_valid():
            system_exit(2, _("\nUnable to register.\nFor further assistance, please contact Red Hat Global Support Services."))

        print(_("System '%s' successfully registered.\n") % identity.name)
        return identity

    def select_service_level(self, org, servicelevel):
        not_supported = _("Error: The service-level command is not supported by the server.")
        try:
            levels = self.cp.getServiceLevelList(org)
        except RemoteServerException as e:
            system_exit(-1, not_supported)
        except RestlibException as e:
            if e.code == 404:
                # no need to die, just skip it
                print(not_supported)
                return None
            else:
                # server supports it but something went wrong, die.
                raise e

        # Create the sla tuple before appending the empty string to the list of
        # valid slas.
        slas = [(sla, sla) for sla in levels]
        # Display an actual message for the empty string level.
        slas.append((_("No service level preference"), ""))

        # The empty string is a valid level so append it to the list.
        levels.append("")
        if servicelevel is None or \
            servicelevel.upper() not in (level.upper() for level in levels):
            if servicelevel is not None:
                print(_("\nService level \"%s\" is not available.") % servicelevel)
            menu = Menu(slas, _("Please select a service level agreement for this system."))
            servicelevel = menu.choose()
        return servicelevel

    def enable_extra_channels(self, subscribed_channels):
        # Check if system was subscribed to extra channels like supplementary, optional, fastrack etc.
        # If so, enable them in the redhat.repo file
        extra_channels = {'supplementary': False, 'productivity': False, 'optional': False}
        for subscribedChannel in subscribed_channels:
            if 'supplementary' in subscribedChannel:
                extra_channels['supplementary'] = True
            elif 'optional' in subscribedChannel:
                extra_channels['optional'] = True
            elif 'productivity' in subscribedChannel:
                extra_channels['productivity'] = True

        if True not in list(extra_channels.values()):
            return

        # create and populate the redhat.repo file
        # use the injection cp_providers consumer auth
        repolib.RepoActionInvoker().update()

        # read in the redhat.repo file
        repofile = repolib.YumRepoFile()
        repofile.read()

        # enable any extra channels we are using and write out redhat.repo
        try:
            for rhsmChannel in repofile.sections():
                if ((extra_channels['supplementary'] and re.search('supplementary$', rhsmChannel)) or
                (extra_channels['optional'] and re.search('optional-rpms$', rhsmChannel)) or
                (extra_channels['productivity'] and re.search('productivity-rpms$', rhsmChannel))):
                    log.debug("Enabling extra channel '%s'" % rhsmChannel)
                    repofile.set(rhsmChannel, 'enabled', '1')
            repofile.write()
        except Exception:
            print(_("\nCouldn't enable extra repositories."))
            command = "subscription-manager repos --help"
            print(_("Please ensure system has subscriptions attached, and see '%s' to enable additional repositories") % command)

    def is_using_systemd(self):
        release_number = int(self.get_release().partition('-')[-1])
        return release_number > 6

    def is_daemon_installed(self, daemon, using_systemd):
        has_systemd_daemon = False
        if using_systemd:
            has_systemd_daemon = subprocess.call("systemctl list-units %s.service | grep %s > /dev/null 2>&1" % (daemon, daemon), shell=True) == 0
        return has_systemd_daemon or os.path.exists("/etc/init.d/%s" % daemon)

    def is_daemon_running(self, daemon, using_systemd):
        if using_systemd:
            return subprocess.call("systemctl is-active --quiet %s" % daemon, shell=True) == 0
        else:
            return subprocess.call("service %s status > /dev/null 2>&1" % daemon, shell=True) == 0

    def handle_legacy_daemons(self, using_systemd):
        print(_("Stopping and disabling legacy services..."))
        log.debug("Attempting to stop and disable legacy services: %s" % " ".join(LEGACY_DAEMONS))
        for daemon in LEGACY_DAEMONS:
            if self.is_daemon_installed(daemon, using_systemd):
                self.disable_daemon(daemon, using_systemd)
                if self.is_daemon_running(daemon, using_systemd):
                    self.stop_daemon(daemon, using_systemd)

    def stop_daemon(self, daemon, using_systemd):
        if using_systemd:
            subprocess.call(["systemctl", "stop", daemon])
        else:
            subprocess.call(["service", daemon, "stop"])

    def disable_daemon(self, daemon, using_systemd):
        if using_systemd:
            subprocess.call(["systemctl", "disable", daemon])
        else:
            subprocess.call(["chkconfig", daemon, "off"])

    def remove_legacy_packages(self):
        print(_("Removing legacy packages..."))
        log.debug("Attempting to remove legacy packages: %s" % " ".join(LEGACY_PACKAGES))
        subprocess.call(["yum", "remove", "-q", "-y"] + LEGACY_PACKAGES)

    def main(self, args=None):
        self.get_auth()
        self.transfer_http_proxy_settings()
        self.cp = self.get_candlepin_connection(self.destination_creds.username, self.destination_creds.password)
        self.check_ok_to_proceed()

        (rpc_session, session_key) = self.connect_to_rhn(self.legacy_creds)
        if self.options.five_to_six:
            self.load_transition_data(rpc_session)
            org = None
            environment = None
        else:
            if self.options.activation_keys:
                environment = None
                org = self.options.org
            else:
                org = self.get_org(self.destination_creds.username)
                environment = self.get_environment(org)

        if self.options.registration_state != "keep":
            self.check_has_access(rpc_session, session_key)

        print()
        print(_("Retrieving existing legacy subscription information..."))
        subscribed_channels = self.get_subscribed_channels_list(rpc_session, session_key)
        self.print_banner(_("System is currently subscribed to these legacy channels:"))
        for channel in subscribed_channels:
            print(channel)

        self.check_for_conflicting_channels(subscribed_channels)
        self.deploy_prod_certificates(subscribed_channels)
        self.clean_up(subscribed_channels)

        self.write_migration_facts()

        if self.options.registration_state == "purge":
            print()
            print(_("Preparing to unregister system from legacy server..."))
            self.legacy_purge(rpc_session, session_key)
        elif self.options.registration_state == "unentitle":
            self.legacy_unentitle(rpc_session)
        else:
            # For the "keep" case, we just leave everything alone.
            pass

        using_systemd = self.is_using_systemd()
        self.handle_legacy_daemons(using_systemd)
        if self.options.remove_legacy_packages:
            self.remove_legacy_packages()

        identity = self.register(self.destination_creds, org, environment)
        if identity:
            self.enable_extra_channels(subscribed_channels)


def add_parser_options(parser, five_to_six_script=False):
    # Careful, the option is --no-auto but we are storing the opposite of its value.
    parser.add_option("-n", "--no-auto", action="store_false", default=True, dest="auto",
        help=_("don't execute the auto-attach option while registering with subscription manager"))
    parser.add_option("-s", "--servicelevel", dest="service_level",
        help=_("service level to follow when attaching subscriptions, for no service "
            "level use --servicelevel=\"\""))
    parser.add_option("--remove-rhn-packages", action="store_true", default=False, dest="remove_legacy_packages",
                      help=_("remove legacy packages"))
    # See BZ 915847 - some users want to connect to RHN with a proxy but to RHSM without a proxy
    parser.add_option("--no-proxy", action="store_true", dest='noproxy',
        help=_("don't use legacy proxy settings with destination server"))

    if five_to_six_script:
        default_registration_state = "unentitle"
        valid_states = ["keep", "unentitle", "purge"]

        parser.add_option("--registration-state", type="choice",
            choices=valid_states, metavar=",".join(valid_states), default=default_registration_state,
            help=_("state to leave system in on legacy server (default is '%s')") % default_registration_state)

    else:
        # The consumerid provides these
        parser.add_option("--org", dest='org',
            help=_("organization to register to"))
        parser.add_option("--environment", dest='environment',
            help=_("environment to register to"))
        parser.add_option("-f", "--force", action="store_true", default=False,
            help=_("ignore channels not available on destination server"))
        # Activation keys can't be used with previously registered IDs so no point in even
        # offering the option for 5to6
        parser.add_option("--activation-key", action="append", dest="activation_keys",
            help=_("activation key to use for registration (can be specified more than once)"))
        # RHN Hosted doesn't allow the "unentitle" option, so instead of
        # using --registration-state with just two options, we'll use a
        # boolean-like option: --keep.
        parser.add_option("--keep", action="store_const", const="keep",
            dest="registration_state", default="purge",
            help=_("leave system registered in legacy environment"))

    parser.add_option("--legacy-user",
        help=_("specify the user name on the legacy server"))
    parser.add_option("--legacy-password",
        help=_("specify the password on the legacy server"))
    parser.add_option("--destination-url",
        help=_("specify the subscription management server to migrate to"))
    parser.add_option("--destination-user",
        help=_("specify the user name on the destination server"))
    parser.add_option("--destination-password",
        help=_("specify the password on the destination server"))


def validate_options(options):
    if options.activation_keys:
        if options.environment:
            system_exit(os.EX_USAGE, _("The --activation-key and --environment options cannot be used together."))
        if options.destination_user or options.destination_password:
            system_exit(os.EX_USAGE, _("The --activation-key option precludes the use of --destination-user and --destination-password"))
        if not options.org:
            system_exit(os.EX_USAGE, _("The --activation-key option requires that a --org be given."))

    if options.service_level and not options.auto:
        # TODO Need to explain why this restriction exists.
        system_exit(os.EX_USAGE, _("The --servicelevel and --no-auto options cannot be used together."))

    if options.remove_legacy_packages and options.registration_state == 'keep' and not options.five_to_six:
        system_exit(os.EX_USAGE, _("The --remove-rhn-packages and --keep options cannot be used together."))

    if options.remove_legacy_packages and options.registration_state in ['keep', 'unentitle'] and options.five_to_six:
        system_exit(os.EX_USAGE, _("The --remove-rhn-packages option must be used with --registration-state=purge."))


def is_hosted():
    rhsmcfg = config.Config(initConfig())
    hostname = rhsmcfg['server']['hostname']
    return bool(re.search('subscription\.rhn\.(.*\.)*redhat\.com', hostname) or
                re.search('subscription\.rhsm\.(.*\.)*redhat\.com', hostname))


def set_defaults(options, five_to_six_script):
    """For options allowed in one script but not the other, we need to supply
    set the attribute on the option object to a sensible default to avoid
    dereferencing an undefined attribute."""
    options.five_to_six = five_to_six_script
    if five_to_six_script:
        options.org = None
        options.environment = None
        options.force = True
        options.activation_keys = None


def main(args=None, five_to_six_script=False):
    parser = OptionParser(usage=USAGE, formatter=WrappedIndentedHelpFormatter())
    add_parser_options(parser, five_to_six_script)

    # In testing we sometimes specify args, otherwise use the default:
    if not args:
        args = sys.argv[1:]

    (options, args) = parser.parse_args(args)
    set_defaults(options, five_to_six_script)
    validate_options(options)
    MigrationEngine(options).main()

    # Try to enable yum plugins: subscription-manager and product-id
    enabled_yum_plugins = repolib.YumPluginManager.enable_pkg_plugins()
    if len(enabled_yum_plugins) > 0:
        print(_('WARNING') + '\n\n' + repolib.YumPluginManager.warning_message(enabled_yum_plugins) + '\n')

    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except IOError as io_err:
        log.error("Error: Unable to print data to stdout/stderr output during exit process: %s" % io_err)


if __name__ == '__main__':
    main()
