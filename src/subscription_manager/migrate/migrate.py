#!/usr/bin/python
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

from datetime import datetime
import getpass
import gettext
import logging
import os
import re
import shutil
import subprocess
import sys
import traceback

import libxml2
from M2Crypto.SSL import SSLError

from rhn import rpclib

import rhsm.config
from rhsm.connection import UEPConnection, RemoteServerException, RestlibException
from rhsm.utils import ServerUrlParseError

_ = gettext.gettext

_LIBPATH = "/usr/share/rhsm"
if _LIBPATH not in sys.path:
    sys.path.append(_LIBPATH)

from subscription_manager import injection as inj
from subscription_manager.identity import ConsumerIdentity
from subscription_manager.cli import system_exit
from subscription_manager.i18n_optparse import OptionParser, \
        USAGE, WrappedIndentedHelpFormatter
from subscription_manager.productid import ProductDatabase
from subscription_manager import repolib
from subscription_manager.utils import parse_server_info
from rhsm import ourjson as json

_RHNLIBPATH = "/usr/share/rhn"
if _RHNLIBPATH not in sys.path:
    sys.path.append(_RHNLIBPATH)

# Don't raise ImportErrors so we can run the unit tests on Fedora.
try:
    from up2date_client.config import initUp2dateConfig
except ImportError:
    def initUp2dateConfig():
        raise NotImplementedError(_("Could not find up2date_client.config module!"))

try:
    from up2date_client.rhnChannel import getChannels
except ImportError:
    def getChannels():
        raise NotImplementedError(_("Could not find up2date_client.rhnChannel module!"))

log = logging.getLogger('rhsm-app.' + __name__)

CONNECTION_FAILURE = _(u"Unable to connect to certificate server: %s.  "
                        "See /var/log/rhsm/rhsm.log for more details.")


FACT_FILE = "/etc/rhsm/facts/migration.facts"

YUM_PLUGIN_CONF = '/etc/yum/pluginconf.d/rhnplugin.conf'

DOUBLE_MAPPED = "rhel-.*?-(client|server)-dts-(5|6)-beta(-debuginfo)?"
#The (?!-beta) bit is a negative lookahead assertion.  So we won't match
#if the 5 or 6 is followed by the word "-beta"
SINGLE_MAPPED = "rhel-.*?-(client|server)-dts-(5|6)(?!-beta)(-debuginfo)?"


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
            selection = raw_input("? ").strip()
            try:
                return self._get_item(selection)
            except InvalidChoiceError:
                self.display_invalid()

    def display(self):
        print self.header
        for index, entry in enumerate(self.choices):
            print "%s. %s" % (index + 1, entry[0])

    def display_invalid(self):
        print _("You have entered an invalid choice.")

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
    def __init__(self):
        self.rhncfg = initUp2dateConfig()
        self.rhsmcfg = rhsm.config.initConfig()

        self.proxy_host = None
        self.proxy_port = None
        self.proxy_user = None
        self.proxy_pass = None

        self.cp = None
        self.db = ProductDatabase()

        self.parser = OptionParser(usage=USAGE, formatter=WrappedIndentedHelpFormatter())
        self.add_parser_options()

    def add_parser_options(self):
        self.parser.add_option("-f", "--force", action="store_true", default=False,
            help=_("ignore channels not available on RHSM"))
        self.parser.add_option("-g", "--gui", action="store_true", default=False, dest='gui',
            help=_("launch the GUI tool to attach subscriptions, instead of auto-attaching"))
        self.parser.add_option("-n", "--no-auto", action="store_true", default=False, dest='noauto',
            help=_("don't execute the auto-attach option while registering with subscription manager"))
        self.parser.add_option("-s", "--servicelevel", dest="servicelevel",
            help=_("service level to follow when attaching subscriptions, for no service "
                "level use --servicelevel=\"\""))
        self.parser.add_option("--serverurl", dest='serverurl',
            help=_("specify the subscription management server to migrate to"))
        self.parser.add_option("--redhat-user", dest="redhatuser",
            help=_("specify the Red Hat user name"))
        self.parser.add_option("--redhat-password", dest="redhatpassword",
            help=_("specify the Red Hat password"))
        self.parser.add_option("--subscription-service-user", dest="subserviceuser",
            help=_("specify the subscription service user name"))
        self.parser.add_option("--subscription-service-password", dest="subservicepassword",
            help=_("specify the subscription service password"))
        # See BZ 915847 - some users want to connect to RHN with a proxy but to RHSM without a proxy
        self.parser.add_option("--no-proxy", action="store_true", dest='noproxy',
            help=_("don't use RHN proxy settings with subscription management server"))
        self.parser.add_option("--org", dest='org',
            help=_("organization to register to"))
        self.parser.add_option("--environment", dest='environment',
            help=_("environment to register to"))

    def validate_options(self):
        if self.options.servicelevel and self.options.noauto:
            system_exit(1, _("The --servicelevel and --no-auto options cannot be used together."))

    def authenticate(self, username, password, user_prompt, pw_prompt):
        if not username:
            username = raw_input(user_prompt).strip()

        if not password:
            password = getpass.getpass(prompt=pw_prompt)

        return UserCredentials(username, password)

    def is_hosted(self):
        hostname = self.rhsmcfg.get('server', 'hostname')
        if re.search('subscription\.rhn\.(.*\.)*redhat\.com', hostname):
            return True  # re.search doesn't return a boolean
        else:
            return False

    def get_auth(self):
        self.rhncreds = self.authenticate(self.options.redhatuser, self.options.redhatpassword,
                _("Red Hat username: "), _("Red Hat password: "))

        if not self.is_hosted() or self.options.serverurl:
            self.secreds = self.authenticate(self.options.subserviceuser, self.options.subservicepassword,
                    _("Subscription Service username: "), _("Subscription Service password: "))
        else:
            self.secreds = self.rhncreds   # make them the same

    def transfer_http_proxy_settings(self):
        if self.rhncfg['enableProxy']:
            http_proxy = self.rhncfg['httpProxy']
            if http_proxy[:7] == "http://":
                http_proxy = http_proxy[7:]
            try:
                self.proxy_host, self.proxy_port = http_proxy.split(':')
            except ValueError, e:
                log.exception(e)
                system_exit(1, _("Unable to read RHN proxy settings."))

            if self.rhncfg['enableProxyAuth']:
                self.proxy_user = self.rhncfg['proxyUser']
                self.proxy_pass = self.rhncfg['proxyPassword']

            log.info("Using proxy %s:%s" % (self.proxy_host, self.proxy_port))
            if self.options.noproxy:
                # If the user doesn't want to use a proxy to connect to their subscription
                # management server, then remove any proxy information that may have crept in.
                self.rhsmcfg.set('server', 'proxy_hostname', '')
                self.rhsmcfg.set('server', 'proxy_port', '')
                self.rhsmcfg.set('server', 'proxy_user', '')
                self.rhsmcfg.set('server', 'proxy_password', '')
            else:
                self.rhsmcfg.set('server', 'proxy_hostname', self.proxy_host)
                self.rhsmcfg.set('server', 'proxy_port', self.proxy_port)
                self.rhsmcfg.set('server', 'proxy_user', self.proxy_user or '')
                self.rhsmcfg.set('server', 'proxy_password', self.proxy_pass or '')
            self.rhsmcfg.save()

    # FIXME: might as well split this into two methods
    def get_candlepin_connection(self, username, password, basic_auth=True):
        try:
            if self.options.serverurl is None:
                hostname = self.rhsmcfg.get('server', 'hostname')
                port = self.rhsmcfg.get_int('server', 'port')
                prefix = self.rhsmcfg.get('server', 'prefix')
            else:
                (hostname, port, prefix) = parse_server_info(self.options.serverurl)
        except ServerUrlParseError, e:
            system_exit(-1, _("Error parsing server URL: %s") % e.msg)

        args = {'host': hostname, 'ssl_port': int(port), 'handler': prefix}
        basic_auth_args = {}

        if basic_auth:
            # FIXME: unused
            basic_auth_args['username'] = username
            basic_auth_args['password'] = password
        else:
            args['cert_file'] = ConsumerIdentity.certpath()
            args['key_file'] = ConsumerIdentity.keypath()

        if not self.options.noproxy:
            args['proxy_hostname_arg'] = self.proxy_host
            args['proxy_port_arg'] = self.proxy_port and int(self.proxy_port)
            args['proxy_user_arg'] = self.proxy_user
            args['proxy_password_arg'] = self.proxy_pass

        self.cp_provider = inj.require(inj.CP_PROVIDER)
        connection_info = args
        self.cp_provider.set_connection_info(**connection_info)

        # FIXME: would be nice to know where can use basic auth or
        #        consumer auth explicitily, so we don't reuse self.cp
        if basic_auth:
            self.cp_provider.set_user_pass(username, password)
            self.cp = self.cp_provider.get_basic_auth_cp()
        else:
            self.cp = self.cp_provider.get_consumer_auth_cp()
        #self.cp = UEPConnection(**args)

    def check_ok_to_proceed(self, username):
        # check if this machine is already registered to Certicate-based RHN
        identity = inj.require(inj.IDENTITY)
        if identity.is_valid():
            print _("\nThis system appears to be already registered to Red Hat Subscription Management.  Exiting.")
            system_exit(1, _("\nPlease visit https://access.redhat.com/management/consumers/%s to view the profile details.") % identity.uuid)

        try:
            self.cp.getOwnerList(username)
        except SSLError, e:
            print _("Error: CA certificate for subscription service has not been installed.")
            system_exit(1, CONNECTION_FAILURE % e)
        except Exception, e:
            log.error(e)
            log.error(traceback.format_exc())
            system_exit(1, CONNECTION_FAILURE % e)

    def get_org(self, username):
        try:
            owner_list = self.cp.getOwnerList(username)
        except Exception, e:
            log.error(e)
            log.error(traceback.format_exc())
            system_exit(1, CONNECTION_FAILURE % e)

        if len(owner_list) == 0:
            system_exit(1, _("%s cannot register with any organizations.") % username)
        else:
            if self.options.org:
                org_input = self.options.org
            elif len(owner_list) == 1:
                org_input = owner_list[0]['key']
            else:
                org_input = raw_input(_("Org: ")).strip()

            org = None
            for owner_data in owner_list:
                if owner_data['key'] == org_input or owner_data['displayName'] == org_input:
                    org = owner_data['key']
                    break
            if not org:
                system_exit(1, _("No such org: %s") % org_input)
        return org

    def get_environment(self, owner_key):
        environment_list = []
        try:
            if self.cp.supports_resource('environments'):
                environment_list = self.cp.getEnvironmentList(owner_key)
            elif self.options.environment:
                system_exit(1, _("Environments are not supported by this server."))
        except Exception, e:
            log.error(e)
            log.error(traceback.format_exc())
            system_exit(1, CONNECTION_FAILURE % e)

        environment = None
        if len(environment_list) > 0:
            if self.options.environment:
                env_input = self.options.environment
            elif len(environment_list) == 1:
                env_input = environment_list[0]['name']
            else:
                env_input = raw_input(_("Environment: ")).strip()

            for env_data in environment_list:
                # See BZ #978001
                if (env_data['name'] == env_input or
                    ('label' in env_data and env_data['label'] == env_input) or
                    ('displayName' in env_data and env_data['displayName'] == env_input)):
                    environment = env_data['name']
                    break
            if not environment:
                system_exit(1, _("No such environment: %s") % env_input)

        return environment

    def connect_to_rhn(self, credentials):
        hostname = self.rhncfg['serverURL'].split('/')[2]
        server_url = 'https://%s/rpc/api' % (hostname)
        try:
            if self.rhncfg['enableProxy']:
                proxy = "%s:%s" % (self.proxy_host, self.proxy_port)
                log.info("Using proxy %s for RHN API methods" % (proxy))
                if self.rhncfg['enableProxyAuth']:
                    proxy = "@".join(["%s:%s" % (self.proxy_user, self.proxy_pass), proxy])
            else:
                proxy = None

            sc = rpclib.Server(server_url, proxy=proxy)

            ca = self.rhncfg["sslCACert"]
            sc.add_trusted_cert(ca)

            sk = sc.auth.login(credentials.username, credentials.password)
            return (sc, sk)
        except Exception:
            log.error(traceback.format_exc())
            system_exit(1, _("Unable to authenticate to RHN Classic.  See /var/log/rhsm/rhsm.log for more details."))

    def check_is_org_admin(self, sc, sk, username):
        try:
            roles = sc.user.listRoles(sk, username)
        except Exception:
            log.error(traceback.format_exc())
            system_exit(1, _("Problem encountered determining user roles in RHN Classic.  Exiting."))
        if "org_admin" not in roles:
            system_exit(1, _("You must be an org admin to successfully run this script."))

    def get_subscribed_channels_list(self):
        try:
            subscribed_channels = map(lambda x: x['label'], getChannels().channels())
        except Exception:
            log.error(traceback.format_exc())
            system_exit(1, _("Problem encountered getting the list of subscribed channels.  Exiting."))
        return subscribed_channels

    def print_banner(self, msg):
        print "\n+-----------------------------------------------------+"
        print msg
        print "+-----------------------------------------------------+"

    def check_for_conflicting_channels(self, subscribed_channels):
        jboss_channel = False
        for channel in subscribed_channels:
            if channel.startswith("jbappplatform"):
                if jboss_channel:
                    system_exit(1, _("You are subscribed to more than one jbappplatform channel."
                                    "  This script does not support that configuration.  Exiting."))
                jboss_channel = True

    def get_release(self):
        f = open('/etc/redhat-release')
        lines = f.readlines()
        f.close()
        release = "RHEL-" + str(lines).split(' ')[6].split('.')[0]
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
        collisions = dict((prod_id, mappings) for prod_id, mappings in applicable_certs.items() if len(mappings) > 1)
        if not collisions:
            return

        log.error("Aborting. Detected the following product ID collisions: %s", collisions)
        self.print_banner(_("Unable to continue migration!"))
        print _("You are subscribed to channels that have conflicting product certificates.")
        for prod_id, mappings in collisions.items():
            # Flatten the list of lists
            colliding_channels = [item for sublist in mappings.values() for item in sublist]
            print _("The following channels map to product ID %s:") % prod_id
            for c in sorted(colliding_channels):
                print "\t%s" % c
        print _("Reduce the number of channels per product ID to 1 and run migration again.")
        print _("To remove a channel, use 'rhn-channel --remove --channel=<conflicting_channel>'.")
        sys.exit(1)

    def deploy_prod_certificates(self, subscribed_channels):
        release = self.get_release()
        mappingfile = "/usr/share/rhsm/product/" + release + "/channel-cert-mapping.txt"
        log.info("Using mapping file %s", mappingfile)

        try:
            dic_data = self.read_channel_cert_mapping(mappingfile)
        except IOError, e:
            log.exception(e)
            system_exit(1, _("Unable to read mapping file: %(mappingfile)s.\n"
                "Do you have the %(package)s package installed?") % {
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
                    log.info("mapping found for: %s = %s", channel, cert)
                    prod_id = cert.split('-')[-1].split('.pem')[0]
                    cert_to_channels = applicable_certs.setdefault(prod_id, {})
                    cert_to_channels.setdefault(cert, []).append(channel)
                else:
                    invalid_rhsm_channels.append(channel)
                    log.info("%s is not mapped to any certificates", channel)
            except Exception:
                unrecognized_channels.append(channel)

        if invalid_rhsm_channels:
            self.print_banner(_("Channels not available on RHSM:"))
            for i in invalid_rhsm_channels:
                print i

        if unrecognized_channels:
            self.print_banner(_("No product certificates are mapped to these RHN Classic channels:"))
            for i in unrecognized_channels:
                print i

        if unrecognized_channels or invalid_rhsm_channels:
            if not self.options.force:
                print(_("\nUse --force to ignore these channels and continue the migration.\n"))
                sys.exit(1)

        # At this point applicable_certs looks something like this
        # { '1': { 'cert-a-1.pem': ['channel1', 'channel2'], 'cert-b-1.pem': ['channel3'] } }
        # This is telling us that product ID 1 maps to two certificates, cert-a and cert-b.
        # Two channels map to the cert-a certificate and one channel maps to cert-b.
        # If we wind up in a situation where a user has channels that map to two different
        # certificates with the same product ID, (e.g. len(hash[product_id]) > 1) we've got a
        # collision and must abort.
        self.handle_collisions(applicable_certs)

        log.info("certs to be installed: %s", applicable_certs)

        self.print_banner(_("Installing product certificates for these RHN Classic channels:"))
        for i in valid_rhsm_channels:
            print i

        release = self.get_release()

        # creates the product directory if it doesn't already exist
        product_dir = inj.require(inj.PROD_DIR)
        db_modified = False
        for cert_to_channels in applicable_certs.values():
            # At this point handle_collisions should have verified that len(cert_to_channels) == 1
            cert, channels = cert_to_channels.items()[0]
            source_path = os.path.join("/usr/share/rhsm/product", release, cert)
            truncated_cert_name = cert.split('-')[-1]
            destination_path = os.path.join(product_dir.path, truncated_cert_name)
            log.info("copying %s to %s ", source_path, destination_path)
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
        print _("\nProduct certificates installed successfully to %s.") % product_dir.path

    def clean_up(self, subscribed_channels):
        #Hack to address BZ 853233
        product_dir = inj.require(inj.PROD_DIR)
        if os.path.isfile(os.path.join(product_dir.path, "68.pem")) and \
            os.path.isfile(os.path.join(product_dir.path), "71.pem"):
            try:
                os.remove(os.path.join(product_dir.path, "68.pem"))
                self.db.delete("68")
                self.db.write()
                log.info("Removed 68.pem due to existence of 71.pem")
            except OSError, e:
                log.info(e)

        #Hack to address double mapping for 180.pem and 17{6|8}.pem
        is_double_mapped = [x for x in subscribed_channels if re.match(DOUBLE_MAPPED, x)]
        is_single_mapped = [x for x in subscribed_channels if re.match(SINGLE_MAPPED, x)]

        if is_double_mapped and is_single_mapped:
            try:
                os.remove(os.path.join(product_dir.path, "180.pem"))
                self.db.delete("180")
                self.db.write()
                log.info("Removed 180.pem")
            except OSError, e:
                log.info(e)

    def get_system_id(self):
        system_id_path = self.rhncfg["systemIdPath"]
        p = libxml2.parseDoc(file(system_id_path).read())
        system_id = int(p.xpathEval('string(//member[* = "system_id"]/value/string)').split('-')[1])
        return system_id

    def write_migration_facts(self):
        migration_date = datetime.now().isoformat()

        if not os.path.exists(FACT_FILE):
            f = open(FACT_FILE, 'w')
            json.dump({"migration.classic_system_id": self.get_system_id(),
                       "migration.migrated_from": "rhn_hosted_classic",
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

    def unregister_system_from_rhn_classic(self, sc, sk):
        system_id_path = self.rhncfg["systemIdPath"]
        system_id = self.get_system_id()

        log.info("Deleting system %s from RHN Classic...", system_id)
        try:
            result = sc.system.deleteSystems(sk, system_id)
        except Exception:
            log.error("Could not delete system %s from RHN Classic" % system_id)
            log.error(traceback.format_exc())
            shutil.move(system_id_path, system_id_path + ".save")
            self.disable_yum_rhn_plugin()
            print _("Did not receive a completed unregistration message from RHN Classic for system %s.\n"
                    "Please investigate on the Customer Portal at https://access.redhat.com.") % system_id
            return

        if result:
            log.info("System %s deleted.  Removing systemid file and disabling rhnplugin.conf", system_id)
            os.remove(system_id_path)
            self.disable_yum_rhn_plugin()
            print _("System successfully unregistered from RHN Classic.")
        else:
            system_exit(1, _("Unable to unregister system from RHN Classic.  Exiting."))

    def register(self, credentials, org, environment):
        # For registering the machine, use the CLI tool to reuse the username/password (because the GUI will prompt for them again)
        # Prepended a \n so translation can proceed without hitch
        print ("")
        print _("Attempting to register system to Red Hat Subscription Management...")
        cmd = ['subscription-manager', 'register', '--username=' + credentials.username, '--password=' + credentials.password]
        if self.options.serverurl:
            cmd.insert(2, '--serverurl=' + self.options.serverurl)

        if org:
            cmd.append('--org=' + org)
        if environment:
            cmd.append('--environment=' + environment)

        result = subprocess.call(cmd)

        identity = inj.require(inj.IDENTITY)
        identity.reload()

        if result != 0:
            system_exit(2, _("\nUnable to register.\nFor further assistance, please contact Red Hat Global Support Services."))
        else:
            print _("System '%s' successfully registered to Red Hat Subscription Management.\n") % identity.name
        return identity

    def select_service_level(self, org, servicelevel):
        not_supported = _("Error: The service-level command is not supported by "
                          "the server.")
        try:
            levels = self.cp.getServiceLevelList(org)
        except RemoteServerException, e:
            system_exit(-1, not_supported)
        except RestlibException, e:
            if e.code == 404:
                # no need to die, just skip it
                print not_supported
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
                print _("\nService level \"%s\" is not available.") % servicelevel
            menu = Menu(slas, _("Please select a service level agreement for this system."))
            servicelevel = menu.choose()
        return servicelevel

    def subscribe(self, consumer, servicelevel):
        # For subscribing, use the GUI tool if the DISPLAY environment variable is set and the gui tool exists
        if os.getenv('DISPLAY') and os.path.exists('/usr/bin/subscription-manager-gui') and self.options.gui:
            print _("Launching the GUI tool to manually attach subscriptions to this system ...")
            result = subprocess.call(['subscription-manager-gui'], stderr=open(os.devnull, 'w'))
        else:
            print _("Attempting to auto-attach to appropriate subscriptions...")
            cmd = ['subscription-manager', 'subscribe', '--auto']

            # only add servicelevel if one was passed in
            if servicelevel:
                cmd.append('--servicelevel=' + servicelevel)

            result = subprocess.call(cmd)
            if result != 0:
                print _("\nUnable to auto-attach.  Do your existing subscriptions match the products installed on this system?")

        # don't show url for katello/CFSE/SAM
        if self.is_hosted():
            print _("\nPlease visit https://access.redhat.com/management/consumers/%s to view the details, and to make changes if necessary.") % consumer.uuid

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

        if True not in extra_channels.values():
            return

        # create and populate the redhat.repo file
        repolib.RepoLib(uep=self.cp).update()

        # read in the redhat.repo file
        repofile = repolib.RepoFile()
        repofile.read()

        # enable any extra channels we are using and write out redhat.repo
        try:
            for rhsmChannel in repofile.sections():
                if ((extra_channels['supplementary'] and re.search('supplementary$', rhsmChannel)) or
                (extra_channels['optional'] and re.search('optional-rpms$', rhsmChannel)) or
                (extra_channels['productivity'] and re.search('productivity-rpms$', rhsmChannel))):
                    log.info("Enabling extra channel '%s'" % rhsmChannel)
                    repofile.set(rhsmChannel, 'enabled', '1')
            repofile.write()
        except Exception:
            print _("\nUnable to enable extra repositories.")
            command = "subscription-manager repos --help"
            print _("Please ensure system has subscriptions attached, and see '%s' to enable additional repositories") % command

    def main(self, args=None):
        # In testing we sometimes specify args, otherwise use the default:
        if not args:
            args = sys.argv[1:]

        (self.options, self.args) = self.parser.parse_args(args)
        self.validate_options()

        self.get_auth()
        self.transfer_http_proxy_settings()
        self.get_candlepin_connection(self.secreds.username, self.secreds.password)
        self.check_ok_to_proceed(self.secreds.username)

        org = self.get_org(self.secreds.username)
        environment = self.get_environment(org)

        (sc, sk) = self.connect_to_rhn(self.rhncreds)
        self.check_is_org_admin(sc, sk, self.rhncreds.username)

        # get a list of RHN classic channels this machine is subscribed to
        # prepending a \n so translation can proceed without hitch
        print ("")
        print _("Retrieving existing RHN Classic subscription information...")
        subscribed_channels = self.get_subscribed_channels_list()
        self.print_banner(_("System is currently subscribed to these RHN Classic Channels:"))
        for channel in subscribed_channels:
            print channel

        self.check_for_conflicting_channels(subscribed_channels)
        self.deploy_prod_certificates(subscribed_channels)
        self.clean_up(subscribed_channels)

        self.write_migration_facts()

        print _("\nPreparing to unregister system from RHN Classic...")
        self.unregister_system_from_rhn_classic(sc, sk)

        # register the system to Certificate-based RHN and consume a subscription
        consumer = self.register(self.secreds, org, environment)

        # fetch new Candlepin connection using the identity cert created by register()
        self.get_candlepin_connection(self.secreds.username, self.secreds.password, basic_auth=False)
        if not self.options.noauto:
            if self.options.servicelevel:
                servicelevel = self.select_service_level(org, self.options.servicelevel)
                self.subscribe(consumer, servicelevel)
            else:
                self.subscribe(consumer, None)

        self.enable_extra_channels(subscribed_channels)

if __name__ == '__main__':
    engine = MigrationEngine().main()
