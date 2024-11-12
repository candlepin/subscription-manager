from ..fixture import SubManFixture
from ..test_managercli import TestCliProxyCommand
from unittest.mock import Mock
from subscription_manager import managercli
from subscription_manager.cache import ContentAccessCache
from subscription_manager.injection import provide, CONTENT_ACCESS_CACHE


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

        self.cc.main([])

        # This cache should not be deleted to be able to use HTTP header 'If-Modified-Since'
        mock_content_access_cache.return_value.remove.assert_not_called()
