from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli
from subscription_manager.cli_command import release

from mock import patch, Mock


class TestReleaseCommand(TestCliProxyCommand):
    command_class = managercli.ReleaseCommand

    def test_main_proxy_url_release(self):
        proxy_host = "example.com"
        proxy_port = "3128"
        proxy_url = "%s:%s" % (proxy_host, proxy_port)

        with patch.object(managercli.ReleaseCommand, '_get_consumer_release'):
            self.cc.main(["--proxy", proxy_url])
            self._orig_do_command()

            # FIXME: too many stubs atm to make this meaningful
            # self.assertEquals(proxy_host, self.cc.cp_provider.content_connection.proxy_hostname)

            self.assertEqual(proxy_url, self.cc.options.proxy_url)
            self.assertEqual(type(proxy_url), type(self.cc.options.proxy_url))
            self.assertEqual(proxy_host, self.cc.proxy_hostname)
            self.assertEqual(int(proxy_port), self.cc.proxy_port)

    def test_release_set_updates_repos(self):
        mock_repo_invoker = Mock()
        with patch.object(release, 'RepoActionInvoker', Mock(return_value=mock_repo_invoker)):
            with patch.object(release.ReleaseBackend, 'get_releases', Mock(return_value=['7.2'])):
                with patch.object(managercli.ReleaseCommand, '_get_consumer_release'):
                    self.cc.main(['--set=7.2'])
                    self._orig_do_command()

                    mock_repo_invoker.update.assert_called_with()

    def test_release_unset_updates_repos(self):
        mock_repo_invoker = Mock()
        with patch.object(release, 'RepoActionInvoker', Mock(return_value=mock_repo_invoker)):
            with patch.object(managercli.ReleaseCommand, '_get_consumer_release'):
                self.cc.main(['--unset'])
                self._orig_do_command()

                mock_repo_invoker.update.assert_called_with()
