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

import sys
import os
import logging
from iniparse import SafeConfigParser
from iniparse.compat import NoOptionError, InterpolationMissingOptionError, NoSectionError
import re
import tempfile
from typing import Dict, List, Optional, Tuple
from subscription_manager.i18n import ugettext as _

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

DEFAULT_CA_CERT_DIR = "/etc/rhsm/ca/"

DEFAULT_ENT_CERT_DIR = "/etc/pki/entitlement"
HOST_ENT_CERT_DIR = "/etc/pki/entitlement-host"

SERVER_DEFAULTS = {
    "hostname": DEFAULT_HOSTNAME,
    "prefix": DEFAULT_PREFIX,
    "port": DEFAULT_PORT,
    "server_timeout": DEFAULT_SERVER_TIMEOUT,
    "insecure": "0",
    "proxy_hostname": "",
    "proxy_scheme": "http",
    "proxy_user": "",
    "proxy_port": "",
    "proxy_password": "",
    "no_proxy": "",
}
RHSM_DEFAULTS = {
    "baseurl": "https://" + DEFAULT_CDN_HOSTNAME,
    "repomd_gpg_url": "",
    "ca_cert_dir": DEFAULT_CA_CERT_DIR,
    "repo_ca_cert": "%(ca_cert_dir)sredhat-uep.pem",
    "productcertdir": "/etc/pki/product",
    "entitlementcertdir": DEFAULT_ENT_CERT_DIR,
    "consumercertdir": "/etc/pki/consumer",
    "manage_repos": "1",
    "full_refresh_on_yum": "0",
    "report_package_profile": "1",
    "plugindir": "/usr/share/rhsm-plugins",
    "pluginconfdir": "/etc/rhsm/pluginconf.d",
    "auto_enable_yum_plugins": "1",
    "package_profile_on_trans": "0",
    "inotify": "1",
    "progress_messages": "1",
    "certificate_algorithms": "legacy",
}

RHSMCERTD_DEFAULTS = {
    "certcheckinterval": "240",
    "splay": "1",
    "disable": "0",
    "auto_registration": "0",
    "auto_registration_interval": "1",
    "auto_registration_identity_interval": "10",
}

LOGGING_DEFAULTS = {
    "default_log_level": "INFO",
}

# Defaults are applied to each section in the config file.
DEFAULTS = {
    "server": SERVER_DEFAULTS,
    "rhsm": RHSM_DEFAULTS,
    "rhsmcertd": RHSMCERTD_DEFAULTS,
    "logging": LOGGING_DEFAULTS,
}


log = logging.getLogger(__name__)


def in_container() -> bool:
    """
    Are we running in a container or not?
    """
    # If the path exists, we are in a container.
    #
    # In UBI containers (RHEL, CentOS), paths HOST_CONFIG_DIR and HOST_ENT_CERT_DIR
    # are symlinks to container's directories:
    #   /etc/rhsm-host            -> /run/secrets/rhsm/
    #   /etc/pki/entitlement-host -> /run/secrets/etc-pki-entitlement/
    #
    # The container secrets are bind-mounted to a directory on the host:
    #   /run/secrets (container)  -> /usr/share/rhel/secrets (host)
    # which is specified in '/usr/share/containers/mounts.conf' (= Podman secret).
    #
    # The directories inside this host's directory are themselves
    # symlinks to other host directories populated by subscription-manager:
    #   /usr/share/rhel/secrets/etc-pki-entitlement -> /etc/pki/entitlement
    #   /usr/share/rhel/secrets/redhat.repo         -> /etc/yum.repos.d/redhat.repo
    #   /usr/share/rhel/secrets/rhsm                -> /etc/rhsm
    #
    # If the container secrets exist, the system is considered to be a container:
    #   /etc/rhsm-host/            exists
    #   /etc/pki/entitlement-host/ exists and is not empty
    if os.path.isdir(HOST_CONFIG_DIR) and (
        os.path.isdir(HOST_ENT_CERT_DIR) and any(os.walk(HOST_ENT_CERT_DIR))
    ):
        log.debug(f"Container detected: found directories {HOST_CONFIG_DIR} and {HOST_ENT_CERT_DIR}.")
        return True
    return False


class RhsmConfigParser(SafeConfigParser):
    """Config file parser for rhsm configuration."""

    # Maps (section, name) to a dict of accepted values for that config key.
    # "values" is a list of valid values and must be defined for every entry.
    # "no_hint" is an optional key that holds values that are accepted but excluded from warnings/hints
    # Add an entry here to enforce validation for any config key.
    VALID_VALUES: Dict[Tuple[str, str], Dict[str, List[str]]] = {
        ("logging", "default_log_level"): {
            "values": ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
            "no_hint": ["NOTSET"],
        },
        ("rhsm", "certificate_algorithms"): {"values": ["legacy", "current"]},
    }

    # defaults unused but kept to preserve compatibility
    def __init__(self, config_file: Optional[str] = None, defaults=None):
        self.config_file: str = config_file
        SafeConfigParser.__init__(self)
        self.read(self.config_file)

    def read(self, file_names: Optional[List[str]] = None) -> List[str]:
        """
        Read configuration files. When configuration files are not specified, then read self.config_file
        :param file_names: list of configuration files
        :return: number of configuration files read
        """
        if file_names is None:
            return super(RhsmConfigParser, self).read(self.config_file)
        else:
            return super(RhsmConfigParser, self).read(file_names)

    def save(self, config_file: Optional[str] = None) -> None:
        """Writes config file to storage."""
        # Use self.config_file if config_file is not provided in method arguments.
        config_file: str = config_file or self.config_file

        rhsm_conf_dir: str = os.path.dirname(config_file)

        # When /etc/rhsm does not exist, then try to create it
        if os.path.isdir(rhsm_conf_dir) is False:
            os.makedirs(rhsm_conf_dir)

        # Create a temporary file to write config data to it and
        # rename the file to the expected config file name after successfully
        # writing all config data.
        # Refer to BZ 1719725: https://bugzilla.redhat.com/show_bug.cgi?id=1719725
        with tempfile.NamedTemporaryFile(mode="w", dir=rhsm_conf_dir, delete=False) as fo:
            self.write(fo)
            fo.flush()
            mode: int
            try:
                mode = os.stat(config_file).st_mode
            except IOError:
                mode = 0o644
            os.rename(fo.name, config_file)
            os.chmod(config_file, mode)

    def get(self, section: str, prop: str) -> str:
        """Get a value from rhsm config.

        :param section: config file section
        :param prop: what config property to find, the config item name
        :return: The string value of the config item.

        If config item exists, but is not set, an empty string is returned.
        """
        try:
            return SafeConfigParser.get(self, section, prop)
        except InterpolationMissingOptionError:
            # if there is an interpolation error, resolve it
            raw_val: str = super(RhsmConfigParser, self).get(section, prop, True)
            interpolations: List[str] = re.findall(r"%\((.*?)\)s", raw_val)
            changed: bool = False
            for interp in interpolations:
                # Defaults aren't interpolated by default, so bake them in as necessary
                # has_option throws an exception if the section doesn't exist,
                # but at this point we know it does.
                if self.has_option(section, interp):
                    super(RhsmConfigParser, self).set(section, interp, self.get(section, interp))
                    changed = True
            if changed:
                # Now that we have the required values, we can interpolate
                return self.get(section, prop)
            # If nothing has been changed (we couldn't fix it) re-raise the exception
            raise
        except (NoOptionError, NoSectionError) as er:
            try:
                return DEFAULTS[section][prop.lower()]
            except KeyError:
                # re-raise the NoOptionError, not the key error
                raise er

    def set(self, section: str, name: str, value: str) -> None:
        try:
            # If the value doesn't exist, or isn't equal, write it
            if self.get(section, name) != value:
                raise NoOptionError
        except Exception:
            if not self.has_section(section):
                self.add_section(section)
            super(RhsmConfigParser, self).set(section, name, value)
        self.is_value_valid(section, name, value)

    def is_value_valid(
        self,
        section: str,
        name: str,
        value: Optional[str],
        print_warning: bool = True,
        raise_on_invalid: bool = False,
    ) -> bool:
        """Check whether a value is valid for the given config key.
        The config key is a tuple of (section, name)

        If the key is not in VALID_VALUES this is a no-op and returns True.
        If the value is invalid and print_warning is True, a warning is printed to stderr.
        If the value is invalid and raise_on_invalid is True, a ValueError is raised.

        :param section: config section
        :param name: config key
        :param value: the value to check
        :param print_warning: print a warning to stderr when the value is invalid
        :param raise_on_invalid: raise ValueError instead of returning False when invalid
        :return: True when the value is valid or the key is unconstrained, otherwise False
        :raises ValueError: when raise_on_invalid is True and the value is invalid
        """
        if (section, name) not in self.VALID_VALUES:
            return True

        values = self.VALID_VALUES[(section, name)]["values"]

        # no_hint is optional, so we must .get() it
        no_hint = self.VALID_VALUES[(section, name)].get("no_hint", [])

        if value in values or value in no_hint:
            return True

        valid_str = ", ".join(values)
        if print_warning:
            print(
                _("Invalid value '{val}' for {section}.{name}.").format(
                    val=value, section=section, name=name
                ),
                file=sys.stderr,
            )
            print(
                _(
                    "Please use:  subscription-manager config --{section}.{name}=<value>"
                    " to set {name} to a valid value."
                ).format(section=section, name=name),
                file=sys.stderr,
            )
            print(_("Valid Values: {valid_str}").format(valid_str=valid_str), file=sys.stderr)
        if raise_on_invalid:
            raise ValueError(
                _("Invalid value '{val}' for {section}.{name}. Valid values are: {valid}.").format(
                    val=value, section=section, name=name, valid=valid_str
                )
            )
        return False

    def get_int(self, section: str, prop: str) -> Optional[int]:
        """Get an int value from the config.

        :param section: the config section
        :param prop: the config item name
        :return:
            An int cast from the string read from.
            If config item is unset, return None.
        :raises ValueError:
            If the config value found can not be coerced into an int
        """
        value_string: str = self.get(section, prop)
        if value_string == "":
            return None
        try:
            value_int = int(value_string)
            # we could also try to handle port name
            # strings (ie, 'http') here with getservbyname
        except (ValueError, TypeError):
            raise ValueError("Section: %s, Property: %s - Integer value expected" % (section, prop))
        return value_int

    # Overriding this method to address
    # http://code.google.com/p/iniparse/issues/detail?id=9
    def defaults(self) -> Dict[str, str]:
        result: List[Tuple[str, str]] = []
        for section in DEFAULTS:
            result += [(key, value) for (key, value) in list(DEFAULTS[section].items())]
        return dict(result)

    def sections(self) -> List[str]:
        result: List[str] = super(RhsmConfigParser, self).sections()
        for section in DEFAULTS:
            if section not in result:
                result.append(section)
        return result

    def has_option(self, section: str, prop: str) -> bool:
        try:
            self.get(section, prop)
            return True
        except NoOptionError:
            return False

    def items(self, section: str) -> List[Tuple[str, str]]:
        result: Dict[str, str] = {}
        for key in DEFAULTS.get(section, {}):
            result[key] = DEFAULTS[section][key]
        if self.has_section(section):
            super_result: List[str] = super(RhsmConfigParser, self).options(section)
            for key in super_result:
                if self.get(section, key) and len(self.get(section, key).strip()) > 0:
                    result[key] = self.get(section, key)
        return list(result.items())

    def options(self, section: str) -> List[str]:
        # This is necessary because with the way we handle defaults, parser.has_section('xyz')
        # will return True if 'xyz' exists only in the defaults but parser.options('xyz')
        #  will throw an exception.
        items = set()
        for key in DEFAULTS.get(section, {}):
            items.add(key)
        if self.has_section(section):
            super_result = super(RhsmConfigParser, self).options(section)
            items.update(super_result)
        return list(items)

    def is_default(self, section: str, prop: str, value: str) -> bool:
        if self.get_default(section, prop) == value:
            return True
        return False

    def has_default(self, section: str, prop: str) -> bool:
        return section in DEFAULTS and prop.lower() in DEFAULTS[section]

    def get_default(self, section: str, prop: str) -> Optional[str]:
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

    def __init__(self, config_file: Optional[str] = None, defaults=None) -> None:
        super().__init__(config_file, defaults)

        # Override the ca_cert_dir and repo_ca_cert if necessary:
        ca_cert_dir: str = self.get("rhsm", "ca_cert_dir")
        repo_ca_cert: str = self.get("rhsm", "repo_ca_cert")

        ca_cert_dir = ca_cert_dir.replace(DEFAULT_CONFIG_DIR, HOST_CONFIG_DIR)
        repo_ca_cert = repo_ca_cert.replace(DEFAULT_CONFIG_DIR, HOST_CONFIG_DIR)
        self.set("rhsm", "ca_cert_dir", ca_cert_dir)
        self.set("rhsm", "repo_ca_cert", repo_ca_cert)

        # Similarly if /etc/pki/entitlement-host exists, override this too.
        # If for some reason the host config is pointing to another directory
        # we leave the config setting alone, our tooling isn't going to be
        # able to handle it anyhow.
        if os.path.exists(HOST_ENT_CERT_DIR):
            ent_cert_dir = self.get("rhsm", "entitlementcertdir")
            if ent_cert_dir == DEFAULT_ENT_CERT_DIR or ent_cert_dir == DEFAULT_ENT_CERT_DIR + "/":
                ent_cert_dir = HOST_ENT_CERT_DIR
            self.set("rhsm", "entitlementcertdir", ent_cert_dir)


CFG: Optional[RhsmConfigParser] = None


def get_config_parser() -> RhsmConfigParser:
    """
    Get an :class:`RhsmConfig` instance

    Will use the first config file defined in the following list:
    - /etc/rhsm-host/rhsm.conf if it exists (only in containers)
    - /etc/rhsm/rhsm.conf
    """
    global CFG

    try:
        CFG = CFG
    except NameError:
        CFG = None

    if CFG is None:
        # Load alternate config file implementation if we detect that we're
        # running in a container.
        if in_container():
            CFG = RhsmHostConfigParser(config_file=os.path.join(HOST_CONFIG_DIR, "rhsm.conf"))
        else:
            CFG = RhsmConfigParser(config_file=DEFAULT_CONFIG_PATH)

    return CFG


# Deprecated but still in use by other applications
def initConfig(configFile=None):
    return get_config_parser()
