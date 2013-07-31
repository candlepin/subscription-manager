#
# This module has been originally modified and enhanced from Red Hat Update
# Agent's config module.
#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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

from iniparse import SafeConfigParser
from iniparse.compat import NoOptionError

DEFAULT_CONFIG_DIR = "/etc/rhsm"
DEFAULT_CONFIG_PATH = "%s/rhsm.conf" % DEFAULT_CONFIG_DIR
DEFAULT_PROXY_PORT = "3128"

# Defaults for connecting to RHN, used to "reset" the configuration file
# if requested by the user:
DEFAULT_HOSTNAME = "subscription.rhn.redhat.com"
DEFAULT_PORT = "443"
DEFAULT_PREFIX = "/subscription"

DEFAULT_CDN_HOSTNAME = "cdn.redhat.com"
DEFAULT_CDN_PORT = "443"
DEFAULT_CDN_PREFIX = "/"

DEFAULT_CA_CERT_DIR = '/etc/rhsm/ca/'

SERVER_DEFAULTS = {
        'hostname': DEFAULT_HOSTNAME,
        'prefix': DEFAULT_PREFIX,
        'port': DEFAULT_PORT,
        'insecure': '0',
        'ssl_verify_depth': '3',
        'proxy_hostname': '',
        'proxy_user': '',
        'proxy_port': '',
        'proxy_password': ''
        }
RHSM_DEFAULTS = {
        'baseurl': 'https://' + DEFAULT_CDN_HOSTNAME,
        'ca_cert_dir': DEFAULT_CA_CERT_DIR,
        'repo_ca_cert': DEFAULT_CA_CERT_DIR + 'redhat-uep.pem',
        'productcertdir': '/etc/pki/product',
        'entitlementcertdir': '/etc/pki/entitlement',
        'consumercertdir': '/etc/pki/consumer',
        'manage_repos': '1',
        'report_package_profile': '1',
        'plugindir': '/usr/share/rhsm-plugins',
        'pluginconfdir': '/etc/rhsm/pluginconf.d'
        }

RHSMCERTD_DEFAULTS = {
        'certcheckinterval': '240',
        'autoattachinterval': '1440'
        }

# Defaults are applied to each section in the config file.
DEFAULTS = {
        'server': SERVER_DEFAULTS,
        'rhsm': RHSM_DEFAULTS,
        'rhsmcertd': RHSMCERTD_DEFAULTS
        }


class RhsmConfigParser(SafeConfigParser):
    """Config file parser for rhsm configuration"""
    # defaults unused but kept to preserve compatibility
    def __init__(self, config_file=None, defaults=None):
        self.config_file = config_file
        SafeConfigParser.__init__(self)
        self.read(self.config_file)

    def save(self, config_file=None):
        """writes config file to storage"""
        fo = open(self.config_file, "wb")
        self.write(fo)

    def get(self, section, prop):
        """get a value from rhsm config

        Args:
            section: config file section
            prop: what config propery to find, he
                config item name
        Returns:
            The string value of the config item.
            If config item exists, but is not set,
            an empty string is return.
        """
        try:
            return SafeConfigParser.get(self, section, prop)
        except Exception, er:
            try:
                return DEFAULTS[section][prop.lower()]
            except KeyError:
                raise er

    def set(self, section, name, value):
        try:
            # If the value doesn't exist, or isn't equal, write it
            if self.get(section, name) != value:
                raise NoOptionError
        except:
            if not self.has_section(section):
                self.add_section(section)
            super(RhsmConfigParser, self).set(section, name, value)

    def get_int(self, section, prop):
        """get a int value from config

        Returns:
            an int cast from the string read from
            the config. If config item is unset,
            return None
        Raises:
            ValueError: if the config value found
                        can not be coerced into an int
        """
        value_string = self.get(section, prop)
        if value_string == "":
            return None
        try:
            value_int = int(value_string)
            # we could also try to handle port name
            # strings (ie, 'http') here with getservbyname
        except (ValueError, TypeError):
            raise ValueError(
                "Section: %s, Property: %s - Integer value expected"
                % (section, prop))
        return value_int

    # Overriding this method to address
    # http://code.google.com/p/iniparse/issues/detail?id=9
    def defaults(self):
        result = []
        for section in DEFAULTS:
            result += [(key, value) for (key, value) in DEFAULTS[section].items()]
        return dict(result)

    def sections(self):
        result = super(RhsmConfigParser, self).sections()
        for section in DEFAULTS:
            if section not in result:
                result.append(section)
        return result

    def has_option(self, section, prop):
        try:
            self.get(section, prop)
            return True
        except NoOptionError:
            return False

    def items(self, section):
        result = {}
        for key in DEFAULTS.get(section, {}):
            result[key] = DEFAULTS[section][key]
        if self.has_section(section):
            super_result = super(RhsmConfigParser, self).options(section)
            for key in super_result:
                result[key] = self.get(section, key)
        return result.items()

    def is_default(self, section, prop, value):
        if self.get_default(section, prop) == value:
            return True
        return False

    def has_default(self, section, prop):
        return section in DEFAULTS and prop.lower() in DEFAULTS[section]

    def get_default(self, section, prop):
        if self.has_default(section, prop.lower()):
            return DEFAULTS[section][prop.lower()]
        return None


def initConfig(config_file=None):
    """get an rhsm config instance"""
    global CFG
    # If a config file was specified, assume we should overwrite the global config
    # to use it. This should only be used in testing. Could be switch to env var?
    if config_file:
        CFG = RhsmConfigParser(config_file=config_file)
        return CFG

    # Normal application behavior, just read the default file if we haven't
    # already:
    try:
        CFG = CFG
    except NameError:
        CFG = None
    if CFG is None:
        CFG = RhsmConfigParser(config_file=DEFAULT_CONFIG_PATH)
    return CFG
