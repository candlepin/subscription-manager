

from fixture import SubManFixture
from subscription_manager.gui import networkConfig
import mock
import rhsm.connection as connection
import rhsm.config
import rhsm.utils
import socket
import stubs


class TestNetworkConfigDialog(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()

    def test_network_cfg_parse_proxy_entry(self):
        self.nc.enableProxyButton.set_active(True)
        proxy_entry = self.nc.proxyEntry

        proxy_entry.set_text("example.com:10000")
        expected = ('example.com', '10000')
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

        proxy_entry.set_text("http://example.com")
        expected = ('example.com', '3128')
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

        proxy_entry.set_text("http://user@example.com")
        expected = ('example.com', '3128')
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

        proxy_entry.set_text("http://user:pass@example.com")
        expected = ('example.com', '3128')
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

        proxy_entry.set_text("example.com:")
        expected = ('example.com', '3128')
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.rhsm.utils.parse_url')
    def test_network_cfg_parse_proxy_entry_unexpected_exception(self, mock_parse_url):
        self.nc.enableProxyButton.set_active(True)
        proxy_entry = self.nc.proxyEntry
        mock_parse_url.side_effect = rhsm.utils.ServerUrlParseError
        proxy_entry.set_text("example.com:10000")
        expected = ('example.com', '10000')
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.rhsm.utils.parse_url')
    def test_network_cfg_parse_proxy_entry_exceptions(self, mock_parse_url):
        self.nc.enableProxyButton.set_active(True)
        proxy_entry = self.nc.proxyEntry
        mock_parse_url.side_effect = rhsm.utils.ServerUrlParseErrorPort
        proxy_entry.set_text("example.com:")
        expected = ('example.com', rhsm.config.DEFAULT_PROXY_PORT)
        actual = self.nc.parse_proxy_entry(proxy_entry.get_text())
        self.assertEquals(expected, actual)

    def test_network_cfg_set_initial_values(self):
        self.stubConfig = stubs.StubConfig(config_file=stubs.test_config)
        self.nc.set_initial_values()

    def test_network_cfg_write_values(self):
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()
        self.nc.cfg = self.stubConfig
        self.nc.enableProxyButton.set_active(True)
        self.nc.proxyEntry.set_text("example.com:10000")
        self.nc.write_values()

    def test_network_cfg_write_values_no_port(self):
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()
        self.nc.cfg = self.stubConfig
        self.nc.enableProxyButton.set_active(True)
        self.nc.proxyEntry.set_text("example.com")
        self.nc.write_values()

    def test_network_cfg_write_values_with_auth(self):
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()
        self.nc.cfg = self.stubConfig
        self.nc.enableProxyButton.set_active(True)
        self.nc.proxyEntry.set_text("example.com:10000")
        self.nc.enableProxyAuthButton.set_active(True)
        self.nc.proxyUserEntry.set_text("redhatUser")
        self.nc.proxyPasswordEntry.set_text("redhatPass")
        self.nc.write_values()

        actual_user = self.nc.cfg.store['server.proxy_user']
        actual_password = self.nc.cfg.store['server.proxy_password']
        self.assertTrue(actual_user == "redhatUser")
        self.assertTrue(actual_password == "redhatPass")

    def test_network_cfg_write_fail(self):
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()
        self.stubConfig.raise_io = True
        self.nc.cfg = self.stubConfig
        self.nc.write_values()

    def test_network_cfg_cancel_preserve_values(self):
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()
        self.nc.cfg = self.stubConfig
        self.nc.enableProxyButton.set_active(True)
        self.nc.proxyEntry.set_text("example.com:10000")
        self.expected = {}
        self.nc.on_cancel_clicked(self.nc.cancelButton)
        self.assertEquals(self.expected, self.nc.cfg.store)

    def test_network_cfg_save_change_values(self):
        self.nc = networkConfig.NetworkConfigDialog()
        self.stubConfig = stubs.StubConfig()
        self.nc.cfg = self.stubConfig
        self.nc.enableProxyButton.set_active(True)
        self.nc.proxyEntry.set_text("example.com:10000")
        self.expected = {}
        self.nc.on_save_clicked(self.nc.saveButton)
        self.assertNotEquals(self.expected, self.nc.cfg.store)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_preserve_socket_timeout(self,
                                                 mock_setdefaulttimeout,
                                                 mock_connection):
        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)
        expected = [mock.call(10), mock.call(self.nc.org_timeout)]
        actual = mock_setdefaulttimeout.call_args_list
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_test_connection(self,
                                         mock_setdefaulttimeout,
                                         mock_connection):

        mock_connection.return_value = True
        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        actual = self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)
        expected = True
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_test_connection_remote_server_exception(self,
                                                                 mock_setdefaulttimeout,
                                                                 mock_connection):

        mock_connection.side_effect = \
        connection.RemoteServerException("RemoteServerException")

        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        actual = self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)

        expected = True
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_test_connection_restlib_exception(self,
                                                           mock_setdefaulttimeout,
                                                           mock_connection):
        mock_connection.side_effect = \
        connection.RestlibException("RestlibException")

        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        actual = self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)

        expected = True
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_test_connection_network_exception(self,
                                                           mock_setdefaulttimeout,
                                                           mock_connection):

        mock_connection.side_effect = \
        connection.NetworkException("NetworkException")

        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        actual = self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)

        expected = False
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_test_connection_unexpected_exception(self,
                                                                mock_setdefaulttimeout,
                                                                mock_connection):

        mock_connection.side_effect = Exception("Made.Up.Exception")

        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        actual = self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)

        expected = False
        self.assertEquals(expected, actual)

    @mock.patch('subscription_manager.gui.networkConfig.connection.UEPConnection.getStatus')
    @mock.patch('subscription_manager.gui.networkConfig.socket.setdefaulttimeout')
    def test_network_cfg_test_connection_socket_error(self,
                                                      mock_setdefaulttimeout,
                                                      mock_connection):
        mock_connection.side_effect = socket.error("socket.error")

        proxy_host = 'example.com'
        proxy_port = '10000'
        proxy_user = ''
        proxy_password = ''
        actual = self.nc.test_connection(proxy_host, proxy_port, proxy_user, proxy_password)

        expected = False
        self.assertEquals(expected, actual)

    def test_network_cfg_on_connection_finish(self):
        connection_status_label = self.nc.connectionStatusLabel
        expected = "Proxy connection succeeded"
        self.nc.on_test_connection_finish(True)
        actual = connection_status_label.get_text()
        self.assertEquals(expected, actual)

    def test_network_cfg_on_connection_finish_fail(self):
        connection_status_label = self.nc.connectionStatusLabel
        expected = "Proxy connection failed"
        self.nc.on_test_connection_finish(False)
        actual = connection_status_label.get_text()
        self.assertEquals(expected, actual)

    def test_network_cfg_show(self):
        self.nc.show()

    @mock.patch('subscription_manager.gui.networkConfig.threading.Thread')
    def test_network_cfg_on_test_connection_clicked_auth(self, mock_thread):
        self.nc.enableProxyButton.set_active(True)
        proxy_entry = self.nc.proxyEntry
        proxy_entry.set_text("example.com:10000")
        self.nc.enableProxyAuthButton.set_active(True)
        proxy_user_entry = self.nc.proxyUserEntry
        proxy_user_entry.set_text("redhatUser")
        proxy_password_entry = self.nc.proxyPasswordEntry
        proxy_password_entry.set_text("redhatPass")
        test_connection_button = self.nc.testConnectionButton
        self.nc.on_test_connection_clicked(test_connection_button)
        expected = mock.call(args=('example.com', '10000', 'redhatUser', 'redhatPass'),
                             name=mock.ANY, target=mock.ANY)
        actual = mock_thread.call_args_list

        self.assertTrue(expected in actual)

    @mock.patch('subscription_manager.gui.networkConfig.threading.Thread')
    def test_network_cfg_on_test_connection_clicked_no_auth(self, mock_thread):
        self.nc.enableProxyButton.set_active(True)
        proxy_entry = self.nc.proxyEntry
        proxy_entry.set_text("example.com:10000")
        self.nc.enableProxyAuthButton.set_active(False)
        proxy_user_entry = self.nc.proxyUserEntry
        proxy_user_entry.set_text("redhatUser")
        proxy_password_entry = self.nc.proxyPasswordEntry
        proxy_password_entry.set_text("redhatPass")
        test_connection_button = self.nc.testConnectionButton
        self.nc.on_test_connection_clicked(test_connection_button)
        expected = mock.call(args=('example.com', '10000', None, None), name=mock.ANY, target=mock.ANY)
        actual = mock_thread.call_args_list
        self.assertTrue(expected in actual)
