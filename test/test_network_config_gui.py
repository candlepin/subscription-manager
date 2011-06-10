import unittest
import StringIO

import stubs
from subscription_manager.gui import networkConfig
import rhsm.config





class NetworkConfigDialog(unittest.TestCase):
    def test_network_config(self):
        nc = networkConfig.NetworkConfigDialog()

    def test_network_config_write_values(self):
        nc = networkConfig.NetworkConfigDialog()
        stubConfig = stubs.StubConfig()
        nc.cfg = stubConfig
        nc.xml.get_widget("enableProxyButton").set_active(True)
        nc.xml.get_widget("proxyEntry").set_text("example.com:10000")
        nc.writeValues()

    def test_network_config_write_fail(self):
        nc = networkConfig.NetworkConfigDialog()
        stubConfig = stubs.StubConfig()
        stubConfig.raise_io = True
        nc.cfg = stubConfig
        nc.writeValues()
