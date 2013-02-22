

import mock

from subscription_manager import plugins

plugin_manager_patcher = mock.patch("subscription_manager.plugins.PluginManager", spec=plugins.PluginManager)
mock_plugin_manager = plugin_manager_patcher.start()
