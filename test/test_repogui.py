# Copyright (c) 2013 Red Hat, Inc.
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

from mock import Mock
from fixture import SubManFixture
from subscription_manager.gui.reposgui import RepositoriesDialog
from stubs import StubBackend
from subscription_manager.repolib import Repo


class TestReposGui(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.backend = StubBackend()

        self.repo_lib = Mock()
        self.repo_lib.get_repos.return_value = []

        self.override_lib = Mock()
        self.override_lib.repo_lib = self.repo_lib
        self.override_lib.get_overrides.return_value = []

        self.dialog = RepositoriesDialog(self.backend, None)
        self.dialog.override_lib = self.override_lib

    def test_show_dialog_with_no_overrides(self):
        repo = self._create_repo("my_repo", [('enabled', '0'), ('gpgcheck', '0')])
        self.repo_lib.get_repos.return_value = [repo]
        self.dialog.show()

        # Check that the model is populated correctly
        store = self.dialog.overrides_store
        tree_iter = store.get_iter_first()
        self.assertTrue(tree_iter is not None)
        self.assertTrue(store.iter_next(tree_iter) is None)

        self.assertEquals("my_repo", store.get_value(tree_iter, store['repo_id']))
        self.assertFalse(store.get_value(tree_iter, store['enabled']))
        # has no overrides so make sure that we are not modified
        self.assertFalse(store.get_value(tree_iter, store['modified']))
        self.assertEquals("MY_REPO", store.get_value(tree_iter, store['name']))
        self.assertEquals('http://foo.bar', store.get_value(tree_iter, store['baseurl']))
        self.assertFalse(store.get_value(tree_iter, store['gpgcheck']))
        # This will be False if there is an override that modifies the gpgcheck value
        self.assertFalse(store.get_value(tree_iter, store['gpgcheck_modified']))

        # verify that the model stores the correct override info for this repo
        override_data = store.get_value(tree_iter, store['override_data'])
        self.assertTrue(override_data is None)

        # Check that the correct repo was stored in the model
        self.assertEquals(repo, store.get_value(tree_iter, store['repo_data']))

        # Check that the details view is populated correctly
        name = self._get_text(self.dialog.name_text)
        self.assertEquals("MY_REPO", name)

        baseurl = self._get_text(self.dialog.baseurl_text)
        self.assertEquals("http://foo.bar", baseurl)

        # Gpgcheck was not overridden so the edit button should be enabled
        # and the label should be 'Enabled'
        self.assertFalse(self.dialog.gpgcheck_remove_button.props.visible)
        self.assertFalse(self.dialog.gpgcheck_combo_box.props.visible)

        gpgcheck_text = self._get_text(self.dialog.gpgcheck_text)
        self.assertEquals("Disabled", gpgcheck_text)
        self.assertTrue(self.dialog.gpgcheck_edit_button.props.visible)
        self.assertTrue(self.dialog.gpgcheck_edit_button.props.sensitive)

    def test_show_dialog_with_overrides(self):
        repo = self._create_repo("my_repo", [('enabled', '0')])
        self.repo_lib.get_repos.return_value = [repo]
        self.override_lib.get_overrides.return_value = [
            {'contentLabel': 'my_repo', 'name': 'enabled', 'value': '1'},
            {'contentLabel': 'my_repo', 'name': 'gpgcheck', 'value': '0'}
        ]
        self.dialog.show()

        # Check that the model is populated correctly
        store = self.dialog.overrides_store
        tree_iter = store.get_iter_first()
        self.assertTrue(tree_iter is not None)
        self.assertTrue(store.iter_next(tree_iter) is None)

        self.assertEquals("my_repo", store.get_value(tree_iter, store['repo_id']))
        self.assertTrue(store.get_value(tree_iter, store['enabled']))
        # has overrides so make sure that we are modified
        self.assertTrue(store.get_value(tree_iter, store['modified']))
        # make sure that there is an icon since we are modified
        self.assertTrue(store.get_value(tree_iter, store['modified-icon']) is not None)
        self.assertEquals("MY_REPO", store.get_value(tree_iter, store['name']))
        self.assertEquals('http://foo.bar', store.get_value(tree_iter, store['baseurl']))
        self.assertFalse(store.get_value(tree_iter, store['gpgcheck']))
        # This will be True if there is an override that modifies the gpgcheck value
        self.assertTrue(store.get_value(tree_iter, store['gpgcheck_modified']))

        # verify that the model stores the correct override info for this repo
        override_data = store.get_value(tree_iter, store['override_data'])
        self.assertEquals(2, len(override_data))
        self.assertTrue('enabled' in override_data)
        self.assertEquals('1', override_data['enabled'])
        self.assertTrue('gpgcheck' in override_data)
        self.assertEquals('0', override_data['gpgcheck'])

        # Check that the correct repo was stored in the model
        self.assertEquals(repo, store.get_value(tree_iter, store['repo_data']))

        # Check that the details view is populated correctly
        name = self._get_text(self.dialog.name_text)
        self.assertEquals("MY_REPO", name)

        baseurl = self._get_text(self.dialog.baseurl_text)
        self.assertEquals("http://foo.bar", baseurl)

        # Check the state of the gpgcheck editing widgets
        self.assertFalse(self.dialog.gpgcheck_text.props.visible)
        self.assertFalse(self.dialog.gpgcheck_edit_button.props.visible)

        self.assertTrue(self.dialog.gpgcheck_combo_box.props.visible)
        self.assertTrue(self.dialog.gpgcheck_combo_box.props.sensitive)
        self.assertFalse(self._get_combo_box_value(self.dialog.gpgcheck_combo_box))
        self.assertTrue(self.dialog.gpgcheck_remove_button.props.visible)
        self.assertTrue(self.dialog.gpgcheck_remove_button.props.sensitive)

    def test_remove_all_button_disabled_when_repo_has_no_modifications(self):
        self.repo_lib.get_repos.return_value = [self._create_repo("my_repo", [('enabled', '0')])]
        self.dialog.show()
        self.assertFalse(self.dialog.reset_button.props.sensitive)

    def test_remove_all_button_enabled_when_repo_has_modifications(self):
        self.repo_lib.get_repos.return_value = [self._create_repo("my_repo", [('enabled', '0')])]
        self.override_lib.get_overrides.return_value = [
            {'contentLabel': 'my_repo', 'name': 'enabled', 'value': '1'}
        ]
        self.dialog.show()
        self.assertTrue(self.dialog.reset_button.props.sensitive)

    def _create_repo(self, repo_id, attribute_tuple_list):
        attrs = [('name', repo_id.upper()), ('baseurl', 'http://foo.bar')]
        attrs.extend(attribute_tuple_list)
        return Repo(repo_id, attrs)

    def _get_text(self, text_view):
        start, end = text_view.get_buffer().get_bounds()
        return text_view.get_buffer().get_text(start, end)

    def _get_combo_box_value(self, combo_box):
        column = combo_box.get_active()
        return combo_box.get_model()[column][1]
