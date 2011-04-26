import unittest
import StringIO

from subscription_manager.gui import networkConfig
import rhsm.config



# config file is root only, so just fill in a stringbuffer 
cfg_buf = """
hostname = server.example.conf
prefix = /candlepin
port = 8443
insecure = 1
ssl_verify_depth = 3
ca_cert_dir = /etc/rhsm/ca/
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =
[rhsm]
baseurl= https://content.example.com
repo_ca_cert = %(ca_cert_dir)sredhat-uep.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer
[rhsmcertd]
certFrequency = 240
"""

test_config = StringIO.StringIO(cfg_buf)

class StubConfig(rhsm.config.RhsmConfigParser):
    def __init__(self, config_file, defaults=rhsm.config.DEFAULTS):
        rhsm.config.RhsmConfigParser.__init__(self, config_file=test_config, defaults=defaults)
        self.raise_io = None
        self.fileName = "/this/isnt/a/real/config/file"

    def set(self, section, key, value):
        pass

    def save(self, config_file=None):
        if self.raise_io:
            raise IOError
        return None


class NetworkConfigDialog(unittest.TestCase):
    
    def test_network_config(self):
        nc = networkConfig.NetworkConfigDialog()

    def test_network_config_write_values(self):
        nc = networkConfig.NetworkConfigDialog()
        stubConfig = StubConfig(config_file=test_config)
        nc.cfg = stubConfig
        nc.xml.get_widget("enableProxyButton").set_active(True)
        nc.xml.get_widget("proxyEntry").set_text("example.com:10000")
        nc.writeValues()

    def test_network_config_write_fail(self):
        nc = networkConfig.NetworkConfigDialog()
        stubConfig = StubConfig(config_file=test_config)
        stubConfig.raise_io = True
        nc.cfg = stubConfig
        nc.writeValues()
        
