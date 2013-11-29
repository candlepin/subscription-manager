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
from subscription_manager.injection import IDENTITY, require
from subscription_manager.gui.storage import MappedListStore
from subscription_manager.gui.widgets import TextTreeViewColumn, CheckBoxColumn,\
    SelectionWrapper, HasSortableWidget
from subscription_manager.gui.messageWindow import YesNoDialog
from subscription_manager.overrides import Override

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


class RepositoriesDialog(widgets.GladeWidget, HasSortableWidget):
    """
    GTK dialog for managing repositories and their overrides.
    """
    widget_names = ['main_window', 'overrides_treeview', 'reset_button', 'close_button',
                    'name_text', 'gpgcheck_text', 'gpgcheck_combo_box',
                    'gpgcheck_remove_button', 'gpgcheck_edit_button',
                    'baseurl_text', 'no_repos_label_container', 'no_repos_label']

    def __init__(self, backend, parent):
        super(RepositoriesDialog, self).__init__('repositories.glade')

        # We require the backend here so that we can always use its version
        # of Overrides which will guarantee that the CP UEPConnection is up
        # to date.
        # FIXME: We really shouldn't have to worry about our connection info
        #        changing out from under us.
        self.backend = backend
        self.identity = require(IDENTITY)

        self.glade.signal_autoconnect({
                "on_dialog_delete_event": self._on_close,
                "on_close_button_clicked": self._on_close,
                "on_reset_button_clicked": self._on_reset_repo,
                "on_gpgcheck_edit_button_clicked": self._on_gpgcheck_edit_button_clicked,
                "on_gpgcheck_remove_button_clicked": self._on_gpgcheck_remove_button_clicked,
                "on_gpgcheck_combo_box_changed": self._on_gpgcheck_combo_box_changed,
        })

        self.overrides_store = MappedListStore({
            "repo_id": str,
            "enabled": bool,
            "modified": bool,
            "modified-icon": gtk.gdk.Pixbuf,
            "name": str,
            "baseurl": str,
            "gpgcheck": bool,
            "gpgcheck_modified": bool,
            "repo_data": object,
            "override_data": object
        })

        # Change the background color of the no_repos_label_container to the same color
        # as the label's base color. The event container allows us to change the color.
        label_base_color = self.no_repos_label.style.base[gtk.STATE_NORMAL]
        self.no_repos_label_container.modify_bg(gtk.STATE_NORMAL, label_base_color)

        # Gnome will hide all button icons by default (gnome setting),
        # so force the icons to show in this case as there is no button
        # text, just the icon.
        gpgcheck_edit_image = gtk.Image()
        gpgcheck_edit_image.set_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_BUTTON)
        self.gpgcheck_edit_button.set_image(gpgcheck_edit_image)
        self.gpgcheck_edit_button.get_image().show()

        gpgcheck_reset_image = gtk.Image()
        gpgcheck_reset_image.set_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_BUTTON)
        self.gpgcheck_remove_button.set_image(gpgcheck_reset_image)
        self.gpgcheck_remove_button.get_image().show()

        self.overrides_treeview.set_model(self.overrides_store)

        self.modified_icon = self.overrides_treeview.render_icon(gtk.STOCK_APPLY,
                                                                 gtk.ICON_SIZE_MENU)

        sortable_cols = []
        enabled_col = CheckBoxColumn(_("Enabled"), self.overrides_store, 'enabled',
            self._on_enable_repo_toggle)
        self.overrides_treeview.append_column(enabled_col)

        repo_id_col = TextTreeViewColumn(self.overrides_store, _("Repository ID"), 'repo_id',
                                         expand=True)
        self.overrides_treeview.append_column(repo_id_col)
        sortable_cols.append((repo_id_col, 'text', 'repo_id'))

        modified_col = gtk.TreeViewColumn(_("Modified"), gtk.CellRendererPixbuf(),
                                          pixbuf=self.overrides_store['modified-icon'])
        self.overrides_treeview.append_column(modified_col)
        sortable_cols.append((modified_col, 'text', 'modified'))

        self.set_sorts(self.overrides_store, sortable_cols)

        self.overrides_treeview.get_selection().connect('changed', self._on_selection)
        self.overrides_treeview.set_rules_hint(True)

        self.gpgcheck_cb_model = gtk.ListStore(str, bool)
        self.gpgcheck_cb_model.append((_("Enabled"), True))
        self.gpgcheck_cb_model.append((_("Disabled"), False))

        gpgcheck_cell_renderer = gtk.CellRendererText()
        self.gpgcheck_combo_box.pack_start(gpgcheck_cell_renderer, True)
        self.gpgcheck_combo_box.add_attribute(gpgcheck_cell_renderer, "text", 0)
        self.gpgcheck_combo_box.set_model(self.gpgcheck_cb_model)
        self.gpgcheck_combo_box.set_active(0)

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
        self.overrides_store.set_sort_column_id(0, gtk.SORT_ASCENDING)

    def _refresh(self, current_overrides, repo_id_to_select=None):

        overrides_per_repo = {}

        for override in current_overrides:
            repo_id = override.repo_id
            overrides_per_repo.setdefault(repo_id, {})
            overrides_per_repo[repo_id][override.name] = override.value

        self.overrides_store.clear()

        current_repos = self.backend.overrides.repo_lib.get_repos(apply_overrides=False)
        if (current_repos):
            self.overrides_treeview.show()
            self.no_repos_label_container.hide()
        else:
            self.overrides_treeview.hide()
            self.no_repos_label_container.show()

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
            self._set_details_visible(False)
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

        self._set_details_visible(selection.is_valid())
        self.reset_button.set_sensitive(selection.is_valid() and selection['modified'])
        if selection.is_valid():
            gpgcheck_enabled = selection['gpgcheck']
            gpgcheck_str = _("Enabled")
            if not gpgcheck_enabled:
                gpgcheck_str = _("Disabled")

            self.name_text.get_buffer().set_text(selection['name'])
            self.baseurl_text.get_buffer().set_text(selection['baseurl'])
            self.gpgcheck_text.get_buffer().set_text(gpgcheck_str)
            # Used 'not' here because we enabled is index 0 in the model.
            self.gpgcheck_combo_box.set_active(int(not gpgcheck_enabled))
            self._set_gpg_lock_state(not selection['gpgcheck_modified'])

    def _on_close(self, button, event=None):
        self.hide()
        return True

    def _on_enable_repo_toggle(self, override_model_iter, enabled):
        repo = self.overrides_store.get_value(override_model_iter,
                                              self.overrides_store['repo_data'])
        overrides = self.overrides_store.get_value(override_model_iter,
                                              self.overrides_store['override_data'])

        repo_enabled = repo['enabled']
        has_enabled_override = overrides and 'enabled' in overrides

        try:
            if not has_enabled_override and enabled != int(repo_enabled):
                # We get True/False from the model, convert to int so that
                # the override gets the correct value.
                self._add_override(repo.id, "enabled", int(enabled))

            elif has_enabled_override and overrides['enabled'] != repo_enabled:
                self._delete_override(repo.id, 'enabled')
            else:
                # Should only ever be one path here, else we have a UI logic error.
                self._add_override(repo.id, "enabled", int(enabled))
        except Exception, e:
            handle_gui_exception(e, _("Unable to update enabled override."),
                                 self._get_dialog_widget())

    def _on_gpgcheck_combo_box_changed(self, combo_box):
        override_selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                              self.overrides_store)

        # Ignore combo box changes when the dialog is first loadded.
        if not override_selection.is_valid():
            return

        column = self.gpgcheck_combo_box.get_active()
        if column < 0:
            return

        current_cb_value = self.gpgcheck_cb_model[column][1]
        override_value = override_selection['gpgcheck']

        # Ignore combo box changes that are identical to the current model value.
        # This can happen on initial data load.
        if current_cb_value == override_value:
            return

        self._add_override(override_selection['repo_id'], "gpgcheck", int(current_cb_value))

    def _set_gpg_lock_state(self, locked):
        if locked:
            self.gpgcheck_text.show()
            self.gpgcheck_edit_button.show()
            self.gpgcheck_remove_button.hide()
            self.gpgcheck_combo_box.hide()
        else:
            self.gpgcheck_text.hide()
            self.gpgcheck_edit_button.hide()
            self.gpgcheck_remove_button.show()
            self.gpgcheck_combo_box.show()

    def _on_gpgcheck_edit_button_clicked(self, button):
        override_selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                              self.overrides_store)
        if not override_selection.is_valid():
            # TODO Should never happen, but we should update the UI somewho
            # to make sure that nothing bad can happen.
            return

        current_value = override_selection['gpgcheck']
        self.gpgcheck_combo_box.set_active(not current_value)

        # Create an override despite the fact that the values are likely the same.
        try:
            self._add_override(override_selection['repo_id'], "gpgcheck",
                               int(current_value))
        except Exception, e:
            handle_gui_exception(e, _("Unable to update the gpgcheck override."),
                                 self._get_dialog_widget())
            return

        self._set_gpg_lock_state(False)

    def _on_gpgcheck_remove_button_clicked(self, button):
        confirm = YesNoDialog(_("Are you sure you want to remove this override?"),
                                 self._get_dialog_widget(), _("Confirm Override Removal"))
        confirm.connect("response", self._on_remove_gpgcheck_confirmation)

    def _on_remove_gpgcheck_confirmation(self, dialog, response):
        if not response:
            return

        override_selection = SelectionWrapper(self.overrides_treeview.get_selection(),
                                              self.overrides_store)
        if not override_selection.is_valid():
            # TODO Should never happen, but we should update the UI somehow
            # to make sure that nothing bad can happen.
            return

        # Delete the override
        try:
            self._delete_override(override_selection['repo_id'], 'gpgcheck')
        except Exception, e:
            handle_gui_exception(e, _("Unable to delete the gpgcheck override."),
                                 self._get_dialog_widget())
            return
        self._set_gpg_lock_state(True)

    def _set_details_visible(self, visible):
        if visible:
            self.gpgcheck_text.show()
            self.gpgcheck_edit_button.show()
            self.gpgcheck_remove_button.show()
            self.gpgcheck_combo_box.show()
            self.name_text.show()
            self.baseurl_text.show()
        else:
            self.gpgcheck_text.hide()
            self.gpgcheck_edit_button.hide()
            self.gpgcheck_remove_button.hide()
            self.gpgcheck_combo_box.hide()
            self.name_text.hide()
            self.baseurl_text.hide()

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
