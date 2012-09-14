import unittest

import rhsm_display
rhsm_display.set_display()

import mock

from subscription_manager.gui import networkConfig


class NetworkConfigDialog(unittest.TestCase):

    def test_network_config_write_values(self):
        nc = networkConfig.NetworkConfigDialog()
        nc.xml.get_widget("enableProxyButton").set_active(True)
        nc.xml.get_widget("proxyEntry").set_text("example.com:10000")
        # our test config has a disarmed .save, so thism is ok
        nc.writeValues()

    def test_network_config_write_fail(self):
        nc = networkConfig.NetworkConfigDialog()
        # mock the config so we can simulate a write failure
        nc.cfg = mock.Mock()
        nc.cfg.fileName = 'not/an/actual/file'
        nc.cfg.save.side_effect = IOError()
        nc.writeValues()
