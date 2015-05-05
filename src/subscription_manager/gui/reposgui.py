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

from gi.repository import Gtk
from gi.repository import GdkPixbuf

import rhsm.config
from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.gui import widgets

from subscription_manager.injection import IDENTITY, ENT_DIR, require
from subscription_manager.gui.storage import MappedListStore
from subscription_manager.gui.widgets import TextTreeViewColumn, CheckBoxColumn,\
    SelectionWrapper, HasSortableWidget, OverridesTable
from subscription_manager.gui.messageWindow import YesNoDialog
from subscription_manager.overrides import Override

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)

cfg = rhsm.config.initConfig()


class RepositoriesDialog(widgets.SubmanBaseWidget, HasSortableWidget):
    """
    GTK dialog for managing repositories and their overrides.
    """
    widget_names = ['main_window', 'reset_button', 'close_button',
                    'name_text', 'baseurl_text', 'scrolledwindow',
                    'other_overrides_view']
    gui_file = "repositories.glade"

    ENTS_PROVIDE_NO_REPOS = _("Attached subscriptions do not provide any repositories.")
    NO_ATTACHED_SUBS = _("No repositories are available without an attached subscription.")
    REPOS_DISABLED_BY_CFG = _("Repositories disabled by configuration.")

    def __init__(self, backend, parent):
        super(RepositoriesDialog, self).__init__()

        # Set up dynamic elements
        self.overrides_treeview = Gtk.TreeView()
        # Add at-spi because we no longer create this widget from glade
        self.overrides_treeview.get_accessible().set_name("Repository View")
        self.no_repos_label, self.no_repos_label_viewport = widgets.get_scrollable_label()
        self.widget_switcher = widgets.WidgetSwitcher(self.scrolledwindow,
                self.no_repos_label_viewport, self.overrides_treeview)

        # We require the backend here so that we can always use its version
        # of Overrides which will guarantee that the CP UEPConnection is up
        # to date.
        # FIXME: We really shouldn't have to worry about our connection info
        #        changing out from under us.
        self.backend = backend
        self.identity = require(IDENTITY)
        self.ent_dir = require(ENT_DIR)

        self.connect_signals({"on_dialog_delete_event": self._on_close,
                              "on_close_button_clicked": self._on_close,
                              "on_reset_button_clicked": self._on_reset_repo})

        self.overrides_store = MappedListStore({
            "repo_id": str,
            "enabled": bool,
            "modified": bool,
            "modified-icon": GdkPixbuf.Pixbuf,
            "name": str,
            "baseurl": str,
            "gpgcheck": bool,
            "gpgcheck_modified": bool,
            "repo_data": object,
            "override_data": object
        })

        self.other_overrides = OverridesTable(self.other_overrides_view)

        # Change the background color of the no_repos_label_container to the same color
        # as the label's base color. The event container allows us to change the color.
        label_base_color = self.no_repos_label.style.base[Gtk.StateType.NORMAL]
        self.no_repos_label_viewport.modify_bg(Gtk.StateType.NORMAL, label_base_color)

        self.overrides_treeview.set_model(self.overrides_store)

        self.modified_icon = self.overrides_treeview.render_icon(Gtk.STOCK_APPLY,
                                                                 Gtk.IconSize.MENU)

        sortable_cols = []
        enabled_col = CheckBoxColumn(_("Enabled"), self.overrides_store, 'enabled',
            self._on_enable_repo_toggle)
        self.overrides_treeview.append_column(enabled_col)

        gpgcheck_col = CheckBoxColumn(_("Gpgcheck"), self.overrides_store, 'gpgcheck',
            self._on_gpgcheck_toggle_changed)
        self.overrides_treeview.append_column(gpgcheck_col)

        repo_id_col = TextTreeViewColumn(self.overrides_store, _("Repository ID"), 'repo_id',
                                         expand=True)
        self.overrides_treeview.append_column(repo_id_col)
        sortable_cols.append((repo_id_col, 'text', 'repo_id'))

        modified_col = Gtk.TreeViewColumn(_("Modified"), Gtk.CellRendererPixbuf(),
                                          pixbuf=self.overrides_store['modified-icon'])
        self.overrides_treeview.append_column(modified_col)
        sortable_cols.append((modified_col, 'text', 'modified'))

        self.set_sorts(self.overrides_store, sortable_cols)

        self.overrides_treeview.get_selection().connect('changed', self._on_selection)
        self.overrides_treeview.set_rules_hint(True)

        self.main_window.set_transient_for(parent)

    def hide(self):
        self.main_window.hide()

    def show(self):
        self._load_data()
        self.main_window.present()

    def _load_data(self):
        # pull the latest overrides from the cache which will be the ones from the server.
        current_overrides = self.backend.overrides.get_overrides(self.identity.uuid) or []
        self._refresh(current_overrides)
        # By default sort by repo_id
        self.overrides_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

    def _refresh(self, current_overrides, repo_id_to_select=None):
        overrides_per_repo = {}

        for override in current_overrides:
            repo_id = override.repo_id
            overrides_per_repo.setdefault(repo_id, {})
            overrides_per_repo[repo_id][override.name] = override.value

        self.overrides_store.clear()
        self.other_overrides.clear()

        current_repos = self.backend.overrides.repo_lib.get_repos(apply_overrides=False)
        if (current_repos):
            self.widget_switcher.set_active(1)
        else:
            ent_count = len(self.ent_dir.list_valid())
            no_repos_message = self.ENTS_PROVIDE_NO_REPOS
            if ent_count == 0:
                no_repos_message = self.NO_ATTACHED_SUBS
            # Checks config for manage_repos. Output updated according to bz 1139174.
            if cfg.has_option('rhsm', 'manage_repos') and \
                    not int(cfg.get('rhsm', 'manage_repos')):
                no_repos_message = self.REPOS_DISABLED_BY_CFG

            self.no_repos_label.set_markup("<b>%s</b>" % no_repos_message)
            self.widget_switcher.set_active(0)

        # Fetch the repositories from repolib without any overrides applied.
        # We do this so that we can tell if anything has been modified by
        # overrides.
        for repo in current_repos:
            overrides = overrides_per_repo.get(repo.id, None)
            modified = not overrides is None
            enabled = self._get_boolean(self._get_model_value(repo, overrides, 'enabled')[0])
            gpgcheck, gpgcheck_modified = self._get_model_value(repo, overrides, 'gpgcheck')
            gpgcheck = self._get_boolean(gpgcheck)
            self.overrides_store.add_map({
                'enabled': bool(int(enabled)),
                'repo_id': repo.id,
                'modified': modified,
                'modified-icon': self._get_modified_icon(modified),
                'name': repo['name'],
                'baseurl': repo['baseurl'],
                'gpgcheck': gpgcheck,
                'gpgcheck_modified': gpgcheck_modified,
                'repo_data': repo,
                'override_data': overrides
            })

        first_row_iter = self.overrides_store.get_iter_first()
        if not first_row_iter:
            self.reset_button.set_sensitive(False)
        elif repo_id_to_select:
            self._select_by_repo_id(repo_id_to_select)
        else:
            self.overrides_treeview.get_selection().select_iter(first_row_iter)

    def _get_modified_icon(self, modified):
        icon = None
        if modified:
            icon = self.modified_icon
        return icon

    def _get_selected_repo_id(self):
        selected = None
        override_selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                              self.overrides_store)
        if override_selection.is_valid():
            selected = override_selection['repo_id']
        return selected

    def _select_by_repo_id(self, repo_id):
        repo_data = (repo_id, self.overrides_store['repo_id'])
        self.overrides_store.foreach(self._select_repo_row, repo_data)

    def _select_repo_row(self, model, path, tree_iter, repo_data_tuple):
        """
        Passed to model's foreach method to select the row if the repo_id
        matches. Returning True tells foreach to stop processing rows.
        """
        repo_id, check_idx = repo_data_tuple
        row_repo_id = model.get_value(tree_iter, check_idx)
        if repo_id == row_repo_id:
            self.overrides_treeview.get_selection().select_iter(tree_iter)
            return True
        return False

    def _get_boolean(self, override_value):
        # An override value might come in as an int or a boolean string.
        # Try our best to convert it, and default to 0.
        try:
            val = int(override_value)
        except ValueError:
            val = 0
            if override_value is not None and override_value.upper() == "TRUE":
                val = 1
        return bool(val)

    def _get_model_value(self, repo, overrides, property_name):
        if not overrides or not property_name in overrides:
            return (repo[property_name], False)
        return (overrides[property_name], True)

    def _on_reset_repo(self, button):
        selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                     self.overrides_store)

        if not selection.is_valid():
            return

        confirm = YesNoDialog(_("Are you sure you want to remove all overrides for <b>%s</b>?") % selection['repo_id'],
                                 self._get_dialog_widget(), _("Confirm Remove All Overrides"))
        confirm.connect("response", self._on_reset_repo_response)

    def _on_reset_repo_response(self, dialog, response):
        if not response:
            return

        selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                     self.overrides_store)

        if not selection.is_valid():
            return

        repo_id = selection['repo_id']

        try:
            self._delete_all_overrides(repo_id)
        except Exception, e:
            handle_gui_exception(e, _("Unable to reset repository overrides."),
                                 self._get_dialog_widget())

    def _on_selection(self, tree_selection):
        selection = SelectionWrapper(tree_selection, self.overrides_store)

        self.other_overrides.clear()
        self.reset_button.set_sensitive(selection.is_valid() and selection['modified'])
        if selection.is_valid():
            self.name_text.get_buffer().set_text(selection['name'])
            self.baseurl_text.get_buffer().set_text(selection['baseurl'])

            for key, value in (selection['override_data'] or {}).items():
                if key not in ['gpgcheck', 'enabled']:
                    self.other_overrides.add_override(key, value)

    def _on_close(self, button, event=None):
        self.hide()
        return True

    def _on_toggle_changed(self, override_model_iter, enabled, key):
        repo = self.overrides_store.get_value(override_model_iter,
                                              self.overrides_store['repo_data'])
        overrides = self.overrides_store.get_value(override_model_iter,
                                              self.overrides_store['override_data'])

        value = repo[key]
        has_active_override = overrides and key in overrides

        try:
            if not has_active_override and enabled != int(value):
                # We get True/False from the model, convert to int so that
                # the override gets the correct value.
                self._add_override(repo.id, key, int(enabled))

            elif has_active_override and overrides[key] != value:
                self._delete_override(repo.id, key)
            else:
                # Should only ever be one path here, else we have a UI logic error.
                self._add_override(repo.id, key, int(enabled))
        except Exception, e:
            handle_gui_exception(e, _("Unable to update %s override.") % key,
                                 self._get_dialog_widget())

    def _on_enable_repo_toggle(self, override_model_iter, enabled):
        return self._on_toggle_changed(override_model_iter, enabled, 'enabled')

    def _on_gpgcheck_toggle_changed(self, override_model_iter, enabled):
        return self._on_toggle_changed(override_model_iter, enabled, 'gpgcheck')

    def _add_override(self, repo, name, value):
        to_add = Override(repo, name, value)
        current_overrides = self.backend.overrides.add_overrides(self.identity.uuid, [to_add])
        self.backend.overrides.update(current_overrides)
        self._refresh(current_overrides, self._get_selected_repo_id())

    def _delete_override(self, repo, name):
        to_delete = Override(repo, name)
        current_overrides = self.backend.overrides.remove_overrides(self.identity.uuid, [to_delete])
        self.backend.overrides.update(current_overrides)
        self._refresh(current_overrides, self._get_selected_repo_id())

    def _delete_all_overrides(self, repo_id):
        current_overrides = self.backend.overrides.remove_all_overrides(self.identity.uuid, [repo_id])
        self.backend.overrides.update(current_overrides)
        self._refresh(current_overrides, self._get_selected_repo_id())

    def _get_dialog_widget(self):
        return self.main_window
