
import mock
import os
import shutil
import StringIO
from string import Template

# Simple test fixture that sets up some widely used mocks
# and test setup

# create some temp dirs to run tests against instead of /
import tempfile
tmpdir = tempfile.mkdtemp()
subdirs = ['/etc/sysconfig/rhn/',
           '/etc/pki/consumers',
           '/etc/pki/products',
           '/etc/pki/entitlements',
           '/etc/rhsm']
for subdir in subdirs:
    os.makedirs('%s/%s' % (tmpdir, subdir))


# Create faux config class, partially so we don't read the system one
# which is root only, and also so we can use different cert paths, etc
#
# So, why here, in the setup? Because certdirectory class variables that
# are read from the config file, so if we don't populate the path vars
# in the config _before_ the certdirectory module is even loaded, it
# doesn't take. That's kind of terrible, but alas.
#

from rhsm import config
# config file is root only, so just fill in a stringbuffer
cfg_buf_tmp = Template("""
[foo]
bar =
[server]
hostname = server.example.conf
prefix = /candlepin
port = 8443
insecure = 1
ssl_verify_depth = 3
ca_cert_dir = /$testdir/etc/rhsm/ca/
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =

[rhsm]
baseurl= https://content.example.com
repo_ca_cert = %(ca_cert_dir)sredhat-uep.pem
productCertDir = /$testdir/etc/pki/product
entitlementCertDir = /$testdir/etc/pki/entitlement
consumerCertDir = /$testdir/{s/etc/pki/consumer

[rhsmcertd]
certFrequency = 240
""")

cfg_buf = cfg_buf_tmp.safe_substitute(testdir=tmpdir)
#just for completeness, let's write out a test config to
# a file and read it in

test_config_file_path = "%s/etc/rhsm/rhsm.conf" % tmpdir
test_config_file = open(test_config_file_path, 'w+')
test_config_file.write(cfg_buf)


class TestConfig(config.RhsmConfigParser):
    def __init__(self, config_file=None, defaults=config.DEFAULTS):
        if config_file:
            self.fileName = config_file
        config.RhsmConfigParser.__init__(self, config_file=self.fileName, defaults=defaults)
        self.raise_io = None
        self.fileName = config_file
        self.store = {}

    def set(self, section, key, value):
        self.store['%s.%s' % (section, key)] = value

    def save(self, config_file=None):
        if self.raise_io:
            raise IOError
        return None


# create a global CFG object,then replace it with our own that candlepin
# read from a stringio
config.initConfig(config_file=test_config_file_path)
config.CFG = TestConfig(config_file=test_config_file_path)

# we are not actually reading test/rhsm.conf, it's just a placeholder
config.CFG.read(test_config_file_path)


def setUp():
    # mock  ClassicCheck to false, tests can re mock if need be.
    # This avoids reading the file off the filesystem
    rhn_check_patcher = mock.patch('subscription_manager.classic_check.ClassicCheck')
    rhn_check_mock = rhn_check_patcher.start()
    rhn_check_mock_instance = rhn_check_mock.return_value
    rhn_check_mock_instance.is_registered_with_classic.return_value = False


def tearDown():
    shutil.rmtree(tmpdir)
