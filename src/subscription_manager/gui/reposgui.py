from __future__ import print_function, division, absolute_import

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
import logging

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.ga import gtk_compat
from subscription_manager.ga import GObject as ga_GObject
from subscription_manager.ga import GdkPixbuf as ga_GdkPixbuf

import rhsm.config
from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.gui import widgets
from subscription_manager.gui import progress

from subscription_manager.async_utils import AsyncRepoOverridesUpdate
from subscription_manager.injection import IDENTITY, ENT_DIR, require
from subscription_manager.gui.storage import MappedListStore
from subscription_manager.gui.widgets import TextTreeViewColumn, CheckBoxColumn,\
    SelectionWrapper, HasSortableWidget, OverridesTable
from subscription_manager.gui.messageWindow import YesNoDialog
from subscription_manager.overrides import Override

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

cfg = rhsm.config.initConfig()


class RepositoriesDialog(widgets.SubmanBaseWidget, HasSortableWidget):
    """
    GTK dialog for managing repositories and their overrides.
    """
    widget_names = ['main_window', 'reset_button', 'close_button', 'apply_button',
                    'name_text', 'baseurl_text', 'scrolledwindow',
                    'other_overrides_view', 'details_vbox', 'main_content_container',
                    'description_text']
    gui_file = "repositories"

    ENTS_PROVIDE_NO_REPOS = _("Attached subscriptions do not provide any repositories.")
    NO_ATTACHED_SUBS = _("No repositories are available without an attached subscription.")
    REPOS_DISABLED_BY_CFG = _("Repositories disabled by configuration.")

    def __init__(self, backend, parent):
        super(RepositoriesDialog, self).__init__()

        # Label wrapping on resize does not work very well on GTK2+
        # so we resize on the fly.
        if gtk_compat.GTK_COMPAT_VERSION == "2":
            # Set the title to wrap and connect to size-allocate to
            # properly resize the label so that it takes up the most
            # space it can.
            self.description_text.set_line_wrap(True)
            self.description_text.connect('size-allocate', lambda label, size: label.set_size_request(size.width - 1, -1))

            self.name_text.set_line_wrap(True)
            self.name_text.connect('size-allocate', lambda label, size: label.set_size_request(size.width - 1, -1))

            self.baseurl_text.set_line_wrap(True)
            self.baseurl_text.connect('size-allocate', lambda label, size: label.set_size_request(size.width - 1, -1))

        # Set up dynamic elements
        self.overrides_treeview = ga_Gtk.TreeView()
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
        self.async_update = AsyncRepoOverridesUpdate(self.backend.overrides)
        self.identity = require(IDENTITY)
        self.ent_dir = require(ENT_DIR)

        self.connect_signals({"on_dialog_delete_event": self._on_close,
                              "on_close_button_clicked": self._on_close,
                              "on_apply_button_clicked": self._on_apply_request,
                              "on_reset_button_clicked": self._on_reset_repo})

        self.overrides_store = MappedListStore({
            "repo_id": str,
            "enabled": bool,
            "modified": bool,
            "modified-icon": ga_GdkPixbuf.Pixbuf,
            "name": str,
            "baseurl": str,
            "gpgcheck": bool,
            "gpgcheck_modified": bool,
            "repo_data": object,
            "override_data": object
        })

        self.other_overrides = OverridesTable(self.other_overrides_view)

        # FIXME: think this needs get_style_context() and possible a
        # Gtk.StyleProvider for gtk3
        # Change the background color of the no_repos_label_container to the same color
        # as the label's base color. The event container allows us to change the color.
        #label_base_color = self.no_repos_label.get_style_context().base[Gtk.StateType.NORMAL]
        #self.no_repos_label_viewport.modify_bg(Gtk.StateType.NORMAL, label_base_color)

        self.overrides_treeview.set_model(self.overrides_store)

        self.modified_icon = self.overrides_treeview.render_icon(ga_Gtk.STOCK_APPLY,
                                                                 ga_Gtk.IconSize.MENU)

        sortable_cols = []
        enabled_col = CheckBoxColumn(_("Enabled"), self.overrides_store, 'enabled',
            self._on_enable_repo_toggle)
        self.overrides_treeview.append_column(enabled_col)

        gpgcheck_col = CheckBoxColumn(_("Gpgcheck"), self.overrides_store, 'gpgcheck',
            self._on_gpgcheck_toggle_changed)
        self.overrides_treeview.append_column(gpgcheck_col)

        repo_id_col = TextTreeViewColumn(self.overrides_store,
                                         _("Repository ID"),
                                         'repo_id',
                                         expand=True)
        self.overrides_treeview.append_column(repo_id_col)
        sortable_cols.append((repo_id_col, 'text', 'repo_id'))

        modified_col = ga_Gtk.TreeViewColumn(_("Modified"), ga_Gtk.CellRendererPixbuf(),
                                          pixbuf=self.overrides_store['modified-icon'])
        self.overrides_treeview.append_column(modified_col)
        sortable_cols.append((modified_col, 'text', 'modified'))

        self.set_sorts(self.overrides_store, sortable_cols)

        self.overrides_treeview.get_selection().connect('changed', self._on_selection)
        self.overrides_treeview.set_rules_hint(True)

        # Progress bar
        self.pb = None
        self.timer = 0

        self.parent = parent
        self.main_window.set_transient_for(parent)

    def hide(self):
        self.main_window.hide()

    def show(self):
        self._load_data()

    def _load_data(self):
        self._show_progress_bar(_("Loading Repository Data"), _("Retrieving repository data from server."), self.parent)
        self.async_update.load_data(self._on_async_load_data_success, self._on_async_load_data_failure)

    def _on_async_load_data_success(self, current_overrides, current_repos):
        self.overrides_store.set_sort_column_id(0, ga_Gtk.SortType.ASCENDING)
        self._refresh(current_overrides, current_repos)
        self._clear_progress_bar()
        self.main_window.present()
        # By default sort by repo_id

    def _on_async_load_data_failure(self, e):
        self._clear_progress_bar()
        handle_gui_exception(e, _("Unable to load repository data."),
                     self._get_dialog_widget())

    def _refresh(self, current_overrides, current_repos, repo_id_to_select=None):
        # Current overrides from server
        overrides_per_repo = {}

        for override in current_overrides:
            repo_id = override.repo_id
            overrides_per_repo.setdefault(repo_id, {})
            overrides_per_repo[repo_id][override.name] = override.value

        self.apply_button.set_sensitive(False)

        self.overrides_store.clear()
        self.other_overrides.clear()

        self.main_content_container.show_all()

        # Switch the dialog view depending on content availability
        if (current_repos):
            self.widget_switcher.set_active(1)
            self.details_vbox.show()
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

            self.details_vbox.hide()
            self.widget_switcher.set_active(0)

        # Update the table model from our gathered override/repo data
        for repo in current_repos:
            overrides = overrides_per_repo.get(repo.id, None)
            self.overrides_store.add_map(self._build_table_row_data(repo, overrides))

        first_row_iter = self.overrides_store.get_iter_first()
        if not first_row_iter:
            self.reset_button.set_sensitive(False)
        elif repo_id_to_select:
            self._select_by_repo_id(repo_id_to_select)
        else:
            self.overrides_treeview.get_selection().select_iter(first_row_iter)

    def _build_table_row_data(self, repo_data, repo_overrides):
        modified = not repo_overrides is None
        enabled = self._get_boolean(self._get_model_value(repo_data, repo_overrides, 'enabled')[0])
        gpgcheck, gpgcheck_modified = self._get_model_value(repo_data, repo_overrides, 'gpgcheck')
        gpgcheck = self._get_boolean(gpgcheck)

        return {
            'enabled': bool(int(enabled)),
            'repo_id': repo_data.id,
            'modified': modified,
            'modified-icon': self._get_modified_icon(modified),
            'name': repo_data['name'],
            'baseurl': repo_data['baseurl'],
            'gpgcheck': gpgcheck,
            'gpgcheck_modified': gpgcheck_modified,
            'repo_data': repo_data,
            'override_data': repo_overrides
        }

    def _show_progress_bar(self, title, label, progress_parent=None):
        self.pb = progress.Progress(title, label, True)
        self.timer = ga_GObject.timeout_add(100, self.pb.pulse)
        self.pb.set_transient_for(progress_parent or self._get_dialog_widget())

    def _clear_progress_bar(self):
        if self.pb:
            self.pb.hide()
            ga_GObject.source_remove(self.timer)
            self.timer = 0
            self.pb = None

    def _get_modified_icon(self, modified):
        icon = None
        if modified:
            icon = self.modified_icon
        return icon

    def _get_selected_repo_id(self):
        selected = None
        override_selection = SelectionWrapper(self.overrides_treeview.get_selection(), self.overrides_store)
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

        self._show_progress_bar(_("Removing Repository Overrides"), _("Removing all overrides for repository <b>%s</b>") % repo_id)
        self.async_update.remove_all_overrides([repo_id], self._on_async_delete_all_overrides_success,
                                          self._on_async_delete_all_overrides_failure)

    def _on_async_delete_all_overrides_success(self, current_overrides, current_repos):
        selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                     self.overrides_store)

        repo_id = selection['repo_id']
        repo_data = None
        for repo in current_repos:
            if repo_id == repo.id:
                repo_data = repo
                break

        if repo_data:
            override_data = None
            for override in current_overrides:
                if repo_id == override.repo_id:
                    override_data = override
                    break

            row_data = self._build_table_row_data(repo_data, override_data)
            self.overrides_store.update_map(selection.tree_iter, row_data)

        # Update the UI based on the current selection as no selection change is
        # triggered, but data may enable/disable different widgets based on data
        # change.
        self._on_selection(self.overrides_treeview.get_selection())

        self._clear_progress_bar()

    def _on_async_delete_all_overrides_failure(self, e):
        self._clear_progress_bar()
        handle_gui_exception(e, _("Unable to reset repository overrides."),
                     self._get_dialog_widget())

    def _on_selection(self, tree_selection):
        selection = SelectionWrapper(tree_selection, self.overrides_store)

        self.other_overrides.clear()
        reset_enabled = False
        if selection.is_valid():
            overrides = selection['override_data']
            reset_enabled = overrides is not None and len(overrides) > 0

            self.name_text.set_text(selection['name'])
            self.baseurl_text.set_text(selection['baseurl'])

            for key, value in list((selection['override_data'] or {}).items()):
                if key not in ['gpgcheck', 'enabled']:
                    self.other_overrides.add_override(key, value)

        self.reset_button.set_sensitive(reset_enabled)

    def _get_changed_overrides(self):
        override_mapping = {
            'to_add': [],
            'to_remove': []
        }

        # Process each row in the model and build up a mapping of overrides.
        self.overrides_store.foreach(self._get_overrides_for_row, override_mapping)
        return override_mapping

    def _on_apply_request(self, button, event=None):
        override_mapping = self._get_changed_overrides()
        self._apply_override_changes(override_mapping, self._on_update_success)

    def _apply_override_changes(self, override_mapping, success_handler):
        self._show_progress_bar(_("Updating Repository Overrides"), _("Applying override changes to repositories."))
        self.async_update.update_overrides(override_mapping['to_add'], override_mapping['to_remove'],
                                      success_handler, self._on_update_failure)

    def _on_update_success(self, current_overrides, current_repos):
        self._refresh(current_overrides, current_repos, self._get_selected_repo_id())
        self._clear_progress_bar()

    def _on_update_failure(self, e):
        handle_gui_exception(e, _("Unable to update overrides."), self._get_dialog_widget())
        self._clear_progress_bar()

    def _on_close(self, button, event=None):
        override_mapping = self._get_changed_overrides()
        if (len(override_mapping["to_add"]) == 0 and len(override_mapping["to_remove"]) == 0):
            self.close_dialog()
            return True

        # There are changes pending, check if the user would like to save changes.
        confirm = YesNoDialog(_("Repositories have changes. Save changes?"),
                                 self._get_dialog_widget(), _("Save Changes"))
        confirm.connect("response", self._on_apply_changes_on_close_response, override_mapping)

    def _on_apply_changes_on_close_response(self, dialog, response, override_mapping):
        if not response:
            self.close_dialog()
            return
        self._apply_override_changes(override_mapping, self._on_async_close_request)

    def _on_async_close_request(self, current_overrides, current_repos):
        self.close_dialog()

    def close_dialog(self):
        self._clear_progress_bar()
        self.hide()

    def _get_overrides_for_row(self, model, path, iter, override_mapping):
        self._update_override_mapping("gpgcheck", model, path, iter, override_mapping)
        self._update_override_mapping("enabled", model, path, iter, override_mapping)

    def _update_override_mapping(self, attribute, model, path, iter, override_mapping):
        '''
        Process a single model row and determine if an override should be added/removed.
        '''
        repo = model.get_value(iter, model['repo_data'])
        remote_overrides = model.get_value(iter, model['override_data'])

        repo_attribute_value = self._get_boolean(repo[attribute])
        model_attribute_value = self._get_boolean(model.get_value(iter, model[attribute]))
        has_remote_override = remote_overrides and attribute in remote_overrides

        if not has_remote_override and model_attribute_value != repo_attribute_value:
            override_mapping["to_add"].append(Override(repo.id, attribute, str(int(model_attribute_value))))
        elif has_remote_override and model_attribute_value == repo_attribute_value:
            override_mapping["to_remove"].append(Override(repo.id, attribute))

    def _on_toggle_changed(self, override_model_iter, enabled, key):
        '''
        Update the gui based on check box change.
        '''
        repo = self.overrides_store.get_value(override_model_iter,
                                              self.overrides_store['repo_data'])
        overrides = self.overrides_store.get_value(override_model_iter,
                                              self.overrides_store['override_data'])

        current_gpg_check = self._get_boolean(self.overrides_store.get_value(override_model_iter,
                                                                             self.overrides_store['gpgcheck']))
        repo_gpg_check = self._get_boolean(repo['gpgcheck'])

        current_enabled = self._get_boolean(self.overrides_store.get_value(override_model_iter,
                                                                           self.overrides_store['enabled']))
        repo_enabled = self._get_boolean(repo['enabled'])

        has_extra = self._has_extra_overrides(overrides)

        mark_modified = has_extra or repo_gpg_check != current_gpg_check or repo_enabled != current_enabled
        enable_reset = overrides is not None and len(overrides) > 0

        self.reset_button.set_sensitive(enable_reset)
        self.overrides_store.set_value(override_model_iter, self.overrides_store['modified'], mark_modified)
        self.overrides_store.set_value(override_model_iter, self.overrides_store['modified-icon'],
                                       self._get_modified_icon(mark_modified))

        changed = self._get_changed_overrides()
        activate_apply_button = len(changed["to_add"]) != 0 or len(changed["to_remove"]) != 0
        self.apply_button.set_sensitive(activate_apply_button)

    def _has_extra_overrides(self, override_data):
        for key, value in list((override_data or {}).items()):
            if key not in ['gpgcheck', 'enabled']:
                return True
        return False

    def _on_enable_repo_toggle(self, override_model_iter, enabled):
        return self._on_toggle_changed(override_model_iter, enabled, 'enabled')

    def _on_gpgcheck_toggle_changed(self, override_model_iter, enabled):
        return self._on_toggle_changed(override_model_iter, enabled, 'gpgcheck')

    def _get_dialog_widget(self):
        return self.main_window
