#
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

import gettext
import logging

import gtk

from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.gui import widgets
from subscription_manager.injection import IDENTITY, OVERRIDE_STATUS_CACHE, require
from subscription_manager.repolib import RepoLib
from subscription_manager.gui.storage import MappedTreeStore
from subscription_manager.gui.widgets import TextTreeViewColumn, CheckBoxColumn

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class RepositoriesDialog(widgets.GladeWidget):
    """
    GTK dialog for managing repositories and their overrides.
    """
    widget_names = ['main_window', 'overrides_treeview', 'reset_button', 'close_button']

    def __init__(self, backend, parent):
        super(RepositoriesDialog, self).__init__('repositories.glade')
        self.backend = backend
        self.identity = require(IDENTITY)
        self.cache = require(OVERRIDE_STATUS_CACHE)
        self.repo_lib = RepoLib(uep=self.backend.cp_provider.get_consumer_auth_cp())
        self.overrides = {}

        self.glade.signal_autoconnect({
                "on_dialog_delete_event": self._on_close,
                "on_close_button_clicked": self._on_close,
                "on_reset_button_clicked": self._on_reset_repo,
        })

        self.overrides_store = MappedTreeStore({
            "enabled": bool,
            "repo_id": str,
            "modified": str,
        })
        self.overrides_treeview.set_model(self.overrides_store)

        enabled_col = CheckBoxColumn(_("Enabled"), self.overrides_store, 'enabled')
        self.overrides_treeview.append_column(enabled_col)

        repo_id_col = TextTreeViewColumn(self.overrides_store, _("Repository ID"), 'repo_id',
                                         expand=True)
        self.overrides_treeview.append_column(repo_id_col)

        modified_col = TextTreeViewColumn(self.overrides_store, _("Modified"), 'modified')
        self.overrides_treeview.append_column(modified_col)

        self.main_window.set_transient_for(parent)
        self.parent = parent

    def hide(self):
        self.main_window.hide()

    def show(self):
        """Make this dialog visible."""
#        self._init_overrides()
#        self._init_available_repos()

        self._load_data()
        self.main_window.present()

    def _load_data(self):
        print "Loading data..."
        current_repos = [repo.id for repo in self.repo_lib.get_repos()]
        cp = self.backend.cp_provider.get_consumer_auth_cp()
        overrides = self.cache.load_status(cp, self.identity.uuid)

        for override in overrides:
            if not override['contentLabel'] in current_repos:
                continue

            self.overrides[override['contentLabel']] = override


    def _on_reset_repo(self, button):
        print "Resetting overrides on selected repo"

    def _init_overrides(self):
        cp = self.backend.cp_provider.get_consumer_auth_cp()
        overrides = self.cache.load_status(cp, self.identity.uuid)
#        self.loaded_overridees.clear()
        for override_json in overrides:
            repo_label = override_json['contentLabel']
            if repo_label in self.loaded_overrides.keys():
                self.loaded_overrides[repo_label].add_override(override_json)
            else:
                override = OverrideWidgetModel(repo_label)
                override.add_override(override_json)
                self.loaded_overrides[repo_label] = override

        self._refresh_overrides()

    def _on_update_repos(self, button):
        overrides = []
        for override in self.loaded_overrides.values():
            overrides.extend(override.as_json_object())

        # We can't update the content overrides on the server unless
        # we are registered. If not, we just update the overrides in
        # cache.
        if self.identity.is_valid():
            try:
                client = self.backend.cp_provider.get_consumer_auth_cp()
                client.setContentOverrides(self.identity.uuid, overrides)
            except Exception, e:
                handle_gui_exception(e, _("Could not update repository overrides.\n\n%s" % e), self.parent)
                return

        # TODO: Update the content override cache.
        self.cache.write_cache()
        self.hide()


    def _on_close(self, button, event=None):
        self.hide()
        return True

    def _set_refresh_button_state(self):
        num_selected = self.overrides_treeview.get_selection().count_selected_rows()
        self.refresh_button.set_sensitive(num_selected > 0)


class OverrideModel(object):
    '''
    Represents a set of content overrides for a single repo.
    '''
    def __init__(self, repo_label):
        self.repo_label = repo_label

        # Set the defaults
        self.enabled = 1
        self.gpg_check = 1


    def add_override(self, override_json):
        if override_json['name'] == 'enabled' and override_json['value'] == '0':
            self.enabled = 0
        elif override_json['name'] == 'gpg-check' and override_json['value'] == '0':
            self.gpg_check = 0

    def as_json_object(self):
        # return a list in prep for other overrides later on.
        return [
            self._create_override_json(self.repo_label, 'enabled', str(self.enabled)),
            self._create_override_json(self.repo_label, 'gpg-check', str(self.gpg_check))
        ]

    def _create_override_json(self, repo, name, value):
        return {'contentLabel': repo, 'name': name, 'value': value}
