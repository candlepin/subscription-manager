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

import base64
import getpass
import httplib
import libxml2
import logging
import os
import re
import shutil
import simplejson as json
import subprocess
import sys
import traceback
import xmlrpclib
from datetime import datetime
from M2Crypto.SSL import SSLError

import rhsm.config
from rhsm.connection import UEPConnection, RemoteServerException, RestlibException

import gettext
_ = gettext.gettext

_LIBPATH = "/usr/share/rhsm"
if _LIBPATH not in sys.path:
    sys.path.append(_LIBPATH)

from subscription_manager import repolib
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.certdirectory import ProductDirectory
from subscription_manager.cli import systemExit
from subscription_manager.i18n_optparse import OptionParser, \
     WrappedIndentedHelpFormatter, USAGE
from subscription_manager.utils import parse_server_info, ServerUrlParseError

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

CONNECTION_FAILURE = _(u"Unable to connect to certificate server: %s.  " \
        "See /var/log/rhsm/rhsm.log for more details.")

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


class ProxiedTransport(xmlrpclib.Transport):
    def set_proxy(self, proxy, credentials):
        self.proxy = proxy
        self.credentials = credentials

    def make_connection(self, host):
        self.realhost = host
        return httplib.HTTP(self.proxy)

    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", 'http://%s%s' % (self.realhost, handler))

    def send_host(self, connection, host):
        connection.putheader('Host', self.realhost)
        if self.credentials:
            connection.putheader('Proxy-Authorization', 'Basic ' + self.credentials)


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
        self.proxy_password = None

        self.cp = None

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

    def validate_options(self):
        if self.options.servicelevel and self.options.noauto:
            systemExit(1, _("The --servicelevel and --no-auto options cannot be used together."))

    def authenticate(self, prompt):
        username = raw_input(prompt).strip()
        password = getpass.getpass()
        return UserCredentials(username, password)

    def is_hosted(self):
        hostname = self.rhsmcfg.get('server', 'hostname')
        if re.search('subscription\.rhn\.(.*\.)*redhat\.com', hostname):
            return True  # re.search doesn't return a boolean
        else:
            return False

    def get_auth(self):
        if self.options.serverurl:
            self.rhncreds = self.authenticate(_("Red Hat account: "))
            self.secreds = self.authenticate(_("System Engine Username: "))
        else:
            self.rhncreds = self.authenticate(_("Red Hat account: "))
            if not self.is_hosted():
                self.secreds = self.authenticate(_("System Engine Username: "))
            else:
                self.secreds = self.rhncreds  # make them the same

    def transfer_http_proxy_settings(self):
        if self.rhncfg['enableProxy']:
            http_proxy = self.rhncfg['httpProxy']
            if http_proxy[:7] == "http://":
                http_proxy = http_proxy[7:]
            try:
                self.proxy_host, self.proxy_port = http_proxy.split(':')
            except ValueError, e:
                log.exception(e)
                systemExit(1, _("Unable to read RHN proxy settings."))

            log.info("Using proxy %s:%s - transferring settings to rhsm.conf" \
                 % (self.proxy_host, self.proxy_port))
            self.rhsmcfg.set('server', 'proxy_hostname', self.proxy_host)
            self.rhsmcfg.set('server', 'proxy_port', self.proxy_port)

            if self.rhncfg['enableProxyAuth']:
                self.proxy_user = self.rhncfg['proxyUser']
                self.proxy_pass = self.rhncfg['proxyPassword']
                self.rhsmcfg.set('server', 'proxy_user', self.proxy_user)
                self.rhsmcfg.set('server', 'proxy_password', self.proxy_pass)
            else:
                self.rhsmcfg.set('server', 'proxy_user', '')
                self.rhsmcfg.set('server', 'proxy_password', '')

            self.rhsmcfg.save()

    def get_candlepin_connection(self, username, password, basic_auth=True):
        try:
            if self.options.serverurl is None:
                hostname = self.rhsmcfg.get('server', 'hostname')
                port = self.rhsmcfg.get('server', 'port')
                prefix = self.rhsmcfg.get('server', 'prefix')
            else:
                (hostname, port, prefix) = parse_server_info(self.options.serverurl)
        except ServerUrlParseError, e:
            systemExit(-1, _("Error parsing server URL: %s") % e.msg)

        proxy_port = self.proxy_port and int(self.proxy_port)

        if basic_auth:
            self.cp = UEPConnection(host=hostname,
                    ssl_port=int(port),
                    handler=prefix,
                    username=username,
                    password=password,
                    proxy_hostname=self.proxy_host,
                    proxy_port=proxy_port,
                    proxy_user=self.proxy_user,
                    proxy_password=self.proxy_password)
        else:
            self.cp = UEPConnection(host=hostname,
                    ssl_port=int(port),
                    handler=prefix,
                    cert_file=ConsumerIdentity.certpath(),
                    key_file=ConsumerIdentity.keypath(),
                    proxy_hostname=self.proxy_host,
                    proxy_port=proxy_port,
                    proxy_user=self.proxy_user,
                    proxy_password=self.proxy_password)

    def check_ok_to_proceed(self, username):
        # check if this machine is already registered to Certicate-based RHN
        if ConsumerIdentity.existsAndValid():
            print _("\nThis system appears to be already registered to Red Hat Subscription Management.  Exiting.")
            consumer = ConsumerIdentity.read()
            systemExit(1, _("\nPlease visit https://access.redhat.com/management/consumers/%s to view the profile details.") % consumer.getConsumerId())

        try:
            self.cp.getOwnerList(username)
        except SSLError, e:
            print _("Error: CA certificate for subscription service has not been installed.")
            systemExit(1, CONNECTION_FAILURE % e)
        except Exception, e:
            log.error(e)
            log.error(traceback.format_exc())
            systemExit(1, CONNECTION_FAILURE % e)

    def get_org(self, username):
        try:
            owner_list = self.cp.getOwnerList(username)
        except Exception, e:
            log.error(e)
            log.error(traceback.format_exc())
            systemExit(1, CONNECTION_FAILURE % e)

        if len(owner_list) == 0:
            systemExit(1, _("%s cannot register to any organizations.") % username)
        elif len(owner_list) > 1:
            org_input = raw_input(_("Org: ")).strip()
            org = None
            for owner_data in owner_list:
                if owner_data['key'] == org_input or owner_data['displayName'] == org_input:
                    org = owner_data['key']
                    break
            if not org:
                systemExit(1, _("No such org: %s") % org_input)
        else:
            org = owner_list[0]['key']

        return org

    def get_environment(self, owner_key):
        environment_list = []
        try:
            if self.cp.supports_resource('environments'):
                environment_list = self.cp.getEnvironmentList(owner_key)
        except Exception, e:
            log.error(e)
            log.error(traceback.format_exc())
            systemExit(1, CONNECTION_FAILURE % e)

        environment = None
        # If we just have one environment, Candlepin will do the right thing
        if len(environment_list) > 1:
            env_input = raw_input(_("Environment: ")).strip()
            for env_data in environment_list:
                if env_data['name'] == env_input or env_data['label'] == env_input:
                    environment = env_data['name']
                    break
            if not environment:
                systemExit(1, _("No such environment: %s") % env_input)

        return environment

    def connect_to_rhn(self, credentials):
        hostname = self.rhncfg['serverURL'].split('/')[2]
        server_url = 'https://%s/rpc/api' % (hostname)
        try:
            if self.rhncfg['enableProxy']:
                pt = ProxiedTransport()
                if self.rhncfg['enableProxyAuth']:
                    proxy_credentials = base64.encodestring('%s:%s' % (self.proxy_user, self.proxy_pass)).strip()
                else:
                    proxy_credentials = ""

                pt.set_proxy("%s:%s" % (self.proxy_host, self.proxy_port), proxy_credentials)
                log.info("Using proxy %s:%s for RHN API methods" % (self.proxy_host, self.proxy_port))
                sc = xmlrpclib.Server(server_url, transport=pt)
            else:
                sc = xmlrpclib.Server(server_url)

            sk = sc.auth.login(credentials.username, credentials.password)
            return (sc, sk)
        except:
            log.error(traceback.format_exc())
            systemExit(1, _("Unable to authenticate to RHN Classic.  See /var/log/rhsm/rhsm.log for more details."))

    def check_is_org_admin(self, sc, sk, username):
        try:
            roles = sc.user.listRoles(sk, username)
        except:
            log.error(traceback.format_exc())
            systemExit(1, _("Problem encountered determining user roles in RHN Classic.  Exiting."))
        if "org_admin" not in roles:
            systemExit(1, _("You must be an org admin to successfully run this script."))

    def get_subscribed_channels_list(self):
        try:
            subscribedChannels = map(lambda x: x['label'], getChannels().channels())
        except:
            log.error(traceback.format_exc())
            systemExit(1, _("Problem encountered getting the list of subscribed channels.  Exiting."))
        return subscribedChannels

    def print_banner(self, msg):
        print "\n+-----------------------------------------------------+"
        print msg
        print "+-----------------------------------------------------+"

    def check_for_conflicting_channels(self, subscribed_channels):
        jboss_channel = False
        for channel in subscribed_channels:
            if channel.startswith("jbappplatform"):
                if jboss_channel:
                    systemExit(1, _("You are subscribed to more than one jbappplatform channel."
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

    def deploy_prod_certificates(self, subscribed_channels):
        release = self.get_release()
        mappingfile = "/usr/share/rhsm/product/" + release + "/channel-cert-mapping.txt"
        log.info("Using mapping file %s", mappingfile)

        try:
            dic_data = self.read_channel_cert_mapping(mappingfile)
        except IOError, e:
            log.exception(e)
            systemExit(1, _("Unable to read mapping file: %s") % mappingfile)

        applicableCerts = []
        validRhsmChannels = []
        invalidRhsmChannels = []
        unrecognizedChannels = []

        for channel in subscribed_channels:
            try:
                if dic_data[channel] != 'none':
                    validRhsmChannels.append(channel)
                    log.info("mapping found for: %s = %s", channel, dic_data[channel])
                    if dic_data[channel] not in applicableCerts:
                        applicableCerts.append(dic_data[channel])
                else:
                    invalidRhsmChannels.append(channel)
                    log.info("%s is not mapped to any certificates", channel)
            except:
                unrecognizedChannels.append(channel)

        if invalidRhsmChannels:
            self.print_banner(_("Channels not available on RHSM:"))
            for i in invalidRhsmChannels:
                print i

        if unrecognizedChannels:
            self.print_banner(_("No product certificates are mapped to these RHN Classic channels:"))
            for i in unrecognizedChannels:
                print i

        if unrecognizedChannels or invalidRhsmChannels:
            if not self.options.force:
                print(_("\nUse --force to ignore these channels and continue the migration.\n"))
                sys.exit(1)

        log.info("certs to be installed: %s", applicableCerts)

        self.print_banner(_("Installing product certificates for these RHN Classic channels:"))
        for i in validRhsmChannels:
            print i

        release = self.get_release()

        # creates the product directory if it doesn't already exist
        productDir = ProductDirectory()
        for cert in applicableCerts:
            source_path = os.path.join("/usr/share/rhsm/product", release, cert)
            truncated_cert_name = cert.split('-')[-1]
            destination_path = os.path.join(str(productDir), truncated_cert_name)
            log.info("copying %s to %s ", source_path, destination_path)
            shutil.copy2(source_path, destination_path)
        print _("\nProduct certificates installed successfully to %s.") % str(productDir)

    def clean_up(self, subscribed_channels):
        #Hack to address BZ 853233
        productDir = ProductDirectory()
        if os.path.isfile(os.path.join(str(productDir), "68.pem")) and \
            os.path.isfile(os.path.join(str(productDir), "71.pem")):
            try:
                os.remove(os.path.join(str(productDir), "68.pem"))
                log.info("Removed 68.pem due to existence of 71.pem")
            except OSError, e:
                log.info(e)

        #Hack to address double mapping for 180.pem and 17{6|8}.pem
        is_double_mapped = [x for x in subscribed_channels if re.match(DOUBLE_MAPPED, x)]
        is_single_mapped = [x for x in subscribed_channels if re.match(SINGLE_MAPPED, x)]

        if is_double_mapped and is_single_mapped:
            try:
                os.remove(os.path.join(str(productDir), "180.pem"))
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

        FACT_FILE = "/etc/rhsm/facts/migration.facts"
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
        YUM_PLUGIN_CONF = '/etc/yum/pluginconf.d/rhnplugin.conf'
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
        systemIdPath = self.rhncfg["systemIdPath"]
        systemId = self.get_system_id()

        log.info("Deleting system %s from RHN Classic...", systemId)
        try:
            result = sc.system.deleteSystems(sk, systemId)
        except:
            log.error("Could not delete system %s from RHN Classic" % systemId)
            log.error(traceback.format_exc())
            shutil.move(systemIdPath, systemIdPath + ".save")
            self.disable_yum_rhn_plugin()
            print _("Did not receive a completed unregistration message from RHN Classic for system %s.\n"
                    "Please investigate on the Customer Portal at https://access.redhat.com.") % systemId
            return

        if result:
            log.info("System %s deleted.  Removing systemid file and disabling rhnplugin.conf", systemId)
            os.remove(systemIdPath)
            self.disable_yum_rhn_plugin()
            print _("System successfully unregistered from RHN Classic.")
        else:
            systemExit(1, _("Unable to unregister system from RHN Classic.  Exiting."))

    def register(self, credentials, org, environment):
        # For registering the machine, use the CLI tool to reuse the username/password (because the GUI will prompt for them again)
        print _("\nAttempting to register system to Red Hat Subscription Management...")
        cmd = ['subscription-manager', 'register', '--username=' + credentials.username, '--password=' + credentials.password]
        if self.options.serverurl:
            cmd.insert(2, '--serverurl=' + self.options.serverurl)

        if org:
            cmd.append('--org=' + org)
        if environment:
            cmd.append('--environment=' + environment)

        result = subprocess.call(cmd)

        if result != 0:
            systemExit(2, _("\nUnable to register.\nFor further assistance, please contact Red Hat Global Support Services."))
        else:
            consumer = ConsumerIdentity.read()
            print _("System '%s' successfully registered to Red Hat Subscription Management.\n") % consumer.getConsumerName()
        return consumer

    def select_service_level(self, org, servicelevel):
        not_supported = _("Error: The service-level command is not supported by "
                          "the server.")
        try:
            levels = self.cp.getServiceLevelList(org)
        except RemoteServerException, e:
            systemExit(-1, not_supported)
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
                print _("\nService level \"%s\" is not available." % servicelevel)
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
            print _("\nPlease visit https://access.redhat.com/management/consumers/%s to view the details, and to make changes if necessary.") % consumer.getConsumerId()

    def enable_extra_channels(self, subscribed_channels):
        # Check if system was subscribed to extra channels like supplementary, optional, fastrack etc.
        # If so, enable them in the redhat.repo file
        extraChannels = {'supplementary': False, 'productivity': False, 'optional': False}
        for subscribedChannel in subscribed_channels:
            if 'supplementary' in subscribedChannel:
                extraChannels['supplementary'] = True
            elif 'optional' in subscribedChannel:
                extraChannels['optional'] = True
            elif 'productivity' in subscribedChannel:
                extraChannels['productivity'] = True

        if True not in extraChannels.values():
            return

        # create and populate the redhat.repo file
        repolib.RepoLib(uep=self.cp).update()

        # read in the redhat.repo file
        repofile = repolib.RepoFile()
        repofile.read()

        # enable any extra channels we are using and write out redhat.repo
        try:
            for rhsmChannel in repofile.sections():
                if ((extraChannels['supplementary'] and re.search('supplementary$', rhsmChannel)) or
                (extraChannels['optional']  and re.search('optional-rpms$', rhsmChannel)) or
                (extraChannels['productivity']  and re.search('productivity-rpms$', rhsmChannel))):
                    log.info("Enabling extra channel '%s'" % rhsmChannel)
                    repofile.set(rhsmChannel, 'enabled', '1')
            repofile.write()
        except:
            print _("\nUnable to enable extra repositories.")
            print _("Please ensure system has subscriptions attached, and see 'subscription-manager repos --help' to enable additional repositories")

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
        print _("\nRetrieving existing RHN Classic subscription information...")
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
