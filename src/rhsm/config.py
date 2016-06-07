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

import os
from iniparse import SafeConfigParser
from iniparse.compat import NoOptionError, InterpolationMissingOptionError, \
        NoSectionError
import re

CONFIG_ENV_VAR = "RHSM_CONFIG"

DEFAULT_CONFIG_DIR = "/etc/rhsm/"
HOST_CONFIG_DIR = "/etc/rhsm-host/"  # symlink inside docker containers
DEFAULT_CONFIG_PATH = "%srhsm.conf" % DEFAULT_CONFIG_DIR
DEFAULT_PROXY_PORT = "3128"
DEFAULT_SERVER_TIMEOUT = "180"

# Defaults for connecting to RHSM, used to "reset" the configuration file
# if requested by the user:
DEFAULT_HOSTNAME = "subscription.rhsm.redhat.com"
DEFAULT_PORT = "443"
DEFAULT_PREFIX = "/subscription"

DEFAULT_CDN_HOSTNAME = "cdn.redhat.com"
DEFAULT_CDN_PORT = "443"
DEFAULT_CDN_PREFIX = "/"

DEFAULT_CA_CERT_DIR = '/etc/rhsm/ca/'

DEFAULT_ENT_CERT_DIR = '/etc/pki/entitlement'
HOST_ENT_CERT_DIR = '/etc/pki/entitlement-host'

SERVER_DEFAULTS = {
        'hostname': DEFAULT_HOSTNAME,
        'prefix': DEFAULT_PREFIX,
        'port': DEFAULT_PORT,
        'server_timeout': DEFAULT_SERVER_TIMEOUT,
        'insecure': '0',
        'ssl_verify_depth': '3',
        'proxy_hostname': '',
        'proxy_user': '',
        'proxy_port': '',
        'proxy_password': '',
        }
RHSM_DEFAULTS = {
        'baseurl': 'https://' + DEFAULT_CDN_HOSTNAME,
        'ca_cert_dir': DEFAULT_CA_CERT_DIR,
        'repo_ca_cert': '%(ca_cert_dir)sredhat-uep.pem',
        'productcertdir': '/etc/pki/product',
        'entitlementcertdir': DEFAULT_ENT_CERT_DIR,
        'consumercertdir': '/etc/pki/consumer',
        'manage_repos': '1',
        'full_refresh_on_yum': '0',
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


def in_container():
    """
    Are we running in a docker container or not?

    Assumes that if we see host rhsm configuration shared with us, we must
    be running in a container.
    """
    if os.path.exists(HOST_CONFIG_DIR):
        return True
    return False


class RhsmConfigParser(SafeConfigParser):
    """Config file parser for rhsm configuration."""
    # defaults unused but kept to preserve compatibility
    def __init__(self, config_file=None, defaults=None):
        self.config_file = config_file
        SafeConfigParser.__init__(self)
        self.read(self.config_file)

    def save(self, config_file=None):
        """Writes config file to storage."""
        fo = open(self.config_file, "wb")
        self.write(fo)

    def get(self, section, prop):
        """Get a value from rhsm config.

        :param section: config file section
        :type section: str
        :param prop: what config propery to find, the config item name
        :type prop: str
        :return: The string value of the config item.
        :rtype: str

        If config item exists, but is not set,
        an empty string is return.
        """
        try:
            return SafeConfigParser.get(self, section, prop)
        except InterpolationMissingOptionError:
            #if there is an interpolation error, resolve it
            raw_val = super(RhsmConfigParser, self).get(section, prop, True)
            interpolations = re.findall("%\((.*?)\)s", raw_val)
            changed = False
            for interp in interpolations:
                # Defaults aren't interpolated by default, so bake them in as necessary
                # has_option throws an exception if the section doesn't exist, but at this point we know it does
                if self.has_option(section, interp):
                    super(RhsmConfigParser, self).set(section, interp, self.get(section, interp))
                    changed = True
            if changed:
                # Now that we have the required values, we can interpolate
                return self.get(section, prop)
            # If nothing has been changed (we couldn't fix it) re-raise the exception
            raise
        except (NoOptionError, NoSectionError), er:
            try:
                return DEFAULTS[section][prop.lower()]
            except KeyError:
                # re-raise the NoOptionError, not the key error
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
        """Get a int value from the config.

        :param section: the config section
        :type section: str
        :param prop: the config item name
        :type prop: str
        :return: An int cast from the string read from
            the config. If config item is unset,
            return None
        :rtype: int or None
        :raises ValueError: if the config value found
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
                if self.get(section, key) and len(self.get(section, key).strip()) > 0:
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


class RhsmHostConfigParser(RhsmConfigParser):
    """
    Sub-class of config parser automatically loaded when we detect that
    we're running in a container environment.

    Host config is shared with containers as /etc/rhsm-host. However the
    rhsm.conf within will still be referencing /etc/rhsm for a couple
    properties. (ca_cert_dir, repo_ca_cert)

    Instead we load config file normally, and assume to replace occurrences
    of /etc/rhsm with /etc/rhsm-host in these properties.

    A similar adjustment is necessary for /etc/pki/entitlement-host if
    present.
    """
    def __init__(self, config_file=None, defaults=None):
        RhsmConfigParser.__init__(self, config_file, defaults)

        # Override the ca_cert_dir and repo_ca_cert if necessary:
        ca_cert_dir = self.get('rhsm', 'ca_cert_dir')
        repo_ca_cert = self.get('rhsm', 'repo_ca_cert')

        ca_cert_dir = ca_cert_dir.replace(DEFAULT_CONFIG_DIR, HOST_CONFIG_DIR)
        repo_ca_cert = repo_ca_cert.replace(DEFAULT_CONFIG_DIR, HOST_CONFIG_DIR)
        self.set('rhsm', 'ca_cert_dir', ca_cert_dir)
        self.set('rhsm', 'repo_ca_cert', repo_ca_cert)

        # Similarly if /etc/pki/entitlement-host exists, override this too.
        # If for some reason the host config is pointing to another directory
        # we leave the config setting alone, our tooling isn't going to be
        # able to handle it anyhow.
        if os.path.exists(HOST_ENT_CERT_DIR):
            ent_cert_dir = self.get('rhsm', 'entitlementcertdir')
            if ent_cert_dir == DEFAULT_ENT_CERT_DIR or \
                    ent_cert_dir == DEFAULT_ENT_CERT_DIR + "/":
                ent_cert_dir = HOST_ENT_CERT_DIR
            self.set('rhsm', 'entitlementcertdir', ent_cert_dir)


def initConfig(config_file=None):
    """
    Get an :class:`RhsmConfig` instance

    Will use the first config file defined in the following list:

    - argument to this method if provided (only for tests)
    - /etc/rhsm-host/rhsm.conf if it exists (only in containers)
    - /etc/rhsm/rhsm.conf
    """
    global CFG
    # If a config file was specified, assume we should overwrite the global config
    # to use it. This should only be used in testing. Could be switch to env var?
    if config_file:
        CFG = RhsmConfigParser(config_file=config_file)
        return CFG

    try:
        CFG = CFG
    except NameError:
        CFG = None
    if CFG is None:

        # Load alternate config file implementation if we detect that we're
        # running in a container.
        if in_container():
            CFG = RhsmHostConfigParser(
                config_file=os.path.join(HOST_CONFIG_DIR, 'rhsm.conf'))
        else:
            CFG = RhsmConfigParser(config_file=DEFAULT_CONFIG_PATH)

    return CFG
