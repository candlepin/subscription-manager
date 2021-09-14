from ..fixture import SubManFixture
from ..test_managercli import TestCliProxyCommand
from mock import Mock
from subscription_manager import managercli
from subscription_manager.cache import ContentAccessCache, \
    ContentAccessModeCache
from subscription_manager.injection import provide, CONTENT_ACCESS_CACHE, \
    CONTENT_ACCESS_MODE_CACHE


class TestRefreshCommand(TestCliProxyCommand):
    command_class = managercli.RefreshCommand

    def test_force_option(self):
        self.cc.main(["--force"])


class TestRefreshCommandWithDoCommand(SubManFixture):
    command_class = managercli.RefreshCommand

    def setUp(self):
        super(TestRefreshCommandWithDoCommand, self).setUp()
        self.cc = self.command_class()

    def test_cache_removed(self):
        # lots of mocking basically to show that the injected content access
        # cache and content access mode caches are cleared on each run of the
        # refresh command
        self.cc.assert_should_be_registered = Mock(return_value=True)
        mock_content_access_cache = Mock(spec=ContentAccessCache)
        mock_content_access_cache.return_value.exists.return_value = True
        provide(CONTENT_ACCESS_CACHE, mock_content_access_cache)
        mock_content_access_mode_cache = Mock(spec=ContentAccessModeCache)
        mock_content_access_mode_cache.return_value.exists.return_value = True
        provide(CONTENT_ACCESS_MODE_CACHE, mock_content_access_mode_cache)
        self.cc.main([])
        mock_content_access_cache.return_value.remove.assert_called_once()
        mock_content_access_mode_cache.return_value.delete_cache.assert_called_once()
        mock_content_access_cache.return_value.exists.assert_called_once()
        mock_content_access_mode_cache.return_value.exists.assert_called_once()
