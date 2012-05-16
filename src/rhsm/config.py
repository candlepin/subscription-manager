#
# This module has been originally modified and enhanced from Red Hat Update Agent's config module.
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

from iniparse import SafeConfigParser


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

# Defaults are applied to each section in the config file.
DEFAULTS = {
                'hostname': 'localhost',
                'prefix': '/candlepin',
                'port': '8443',
                'ca_cert_dir': '/etc/rhsm/ca/',
                'repo_ca_cert': '/etc/rhsm/ca/redhat-uep.pem',
                'ssl_verify_depth': '3',
                'proxy_hostname': '',
                'proxy_port': '',
                'proxy_user': '',
                'proxy_password': '',
                'insecure': '0',
                'baseurl': 'https://cdn.redhat.com',
                'manage_repos': '1',
                'productCertDir': '/etc/pki/product',
                'entitlementCertDir': '/etc/pki/entitlement',
                'consumerCertDir': '/etc/pki/consumer',
                'certFrequency': '240',
                'healFrequency': '1440',
            }


class RhsmConfigParser(SafeConfigParser):
    def __init__(self, config_file=None, defaults=None):
        self.config_file = config_file
        SafeConfigParser.__init__(self, defaults=defaults)
        self.read(self.config_file)

    def save(self, config_file=None):
        fo = open(self.config_file, "wb")
        self.write(fo)

    def get(self, section, prop):
        if not self.has_section(section):
            self.add_section(section)
        return SafeConfigParser.get(self, section, prop)

    # Overriding this method to address
    # http://code.google.com/p/iniparse/issues/detail?id=9
    def defaults(self):
        d = {}
        for name, lineobj in self.data._defaults._options.items():
            d[name] = lineobj.value
        return d


def initConfig(config_file=None):

    global CFG
    # If a config file was specified, assume we should overwrite the global config
    # to use it. This should only be used in testing. Could be switch to env var?
    if config_file:
        CFG = RhsmConfigParser(config_file=config_file, defaults=DEFAULTS)
        return CFG

    # Normal application behavior, just read the default file if we haven't
    # already:
    try:
        CFG = CFG
    except NameError:
        CFG = None
    if CFG == None:
        CFG = RhsmConfigParser(config_file=DEFAULT_CONFIG_PATH, defaults=DEFAULTS)
    return CFG
