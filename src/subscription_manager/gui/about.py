from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2012 Red Hat, Inc.
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
import datetime
import os
import subprocess

from subscription_manager.ga import Gtk as ga_Gtk

from subscription_manager.gui.utils import get_running_as_firstboot
from subscription_manager.utils import get_client_versions, get_server_versions

from subscription_manager.i18n import ugettext as _

LICENSE = _("\nThis software is licensed to you under the GNU General Public License, "
            "version 2 (GPLv2). There is NO WARRANTY for this software, express or "
            "implied, including the implied warranties of MERCHANTABILITY or FITNESS "
            "FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2 "
            "along with this software; if not, see:\n\n"
            "http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt\n\n"
            "Red Hat trademarks are not licensed under GPLv2. No permission is "
            "granted to use or replicate Red Hat trademarks that are incorporated "
            "in this software or its documentation.\n")

AUTO_ATTACH_UPDATE_FILE = '/var/run/rhsm/next_auto_attach_update'
CERT_CHECK_UPDATE_FILE = '/var/run/rhsm/next_cert_check_update'

prefix = os.path.dirname(__file__)


class AboutDialog(object):
    def __init__(self, parent, backend):
        self.backend = backend
        self.dialog = ga_Gtk.AboutDialog()
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.dialog.set_name(_("Subscription Manager"))
        self.dialog.set_license(LICENSE)
        self.dialog.set_wrap_license(True)
        if not get_running_as_firstboot():
            self.dialog.set_website("https://fedorahosted.org/subscription-manager/")
        self.dialog.set_copyright(_("Copyright (c) 2012 Red Hat, Inc."))
        self.dialog.set_logo_icon_name("subscription-manager")
        self.dialog.set_icon_name("subscription-manager")
        self.dialog.set_authors(["The Subscription Manager Team"])

        next_update_label = ga_Gtk.Label()
        next_auto_attach_label = ga_Gtk.Label()
        sub_man_version_label = ga_Gtk.Label()
        backend_version_label = ga_Gtk.Label()
        context_box = self.dialog.vbox.get_children()[0]
        context_box.pack_end(next_auto_attach_label, True, True, 0)
        context_box.pack_end(next_update_label, True, True, 0)
        context_box.pack_end(sub_man_version_label, True, True, 0)
        context_box.pack_end(backend_version_label, True, True, 0)

        self._set_next_update(next_update_label, next_auto_attach_label)

        # Set the component versions.
        server_versions = get_server_versions(self.backend.cp_provider.get_consumer_auth_cp())
        client_versions = get_client_versions()

        sub_man_version_label.set_markup(_("<b>%s version:</b> %s") %
                                        ("subscription manager", client_versions['subscription-manager']))
        backend_version_label.set_markup(_("<b>subscription management service version:</b> %s") %
                                           server_versions['candlepin'])

        self.dialog.connect("response", self._handle_response)
        self.dialog.show_all()

    def show(self):
        self.dialog.show()

    def _handle_response(self, dialog, response):
        if response == ga_Gtk.ResponseType.DELETE_EVENT or response == ga_Gtk.ResponseType.CANCEL:
            self.dialog.destroy()

    def _set_next_update(self, next_update_label, next_auto_attach_label):
        try:
            if self._rhsmcertd_on():
                next_update = int(open(CERT_CHECK_UPDATE_FILE, 'r').read())
                next_auto_attach = int(open(AUTO_ATTACH_UPDATE_FILE, 'r').read())
            else:
                next_update = None
                next_auto_attach = None
        except Exception:
            next_update = None
            next_auto_attach = None

        if next_update:
            update_time = datetime.datetime.fromtimestamp(next_update)
            next_update_label.set_markup(_('<b>Next System Certificate Check:</b> %s') %
                update_time.strftime("%c"))
            next_update_label.show()
        else:
            next_update_label.hide()
        if next_auto_attach:
            next_auto_attach = datetime.datetime.fromtimestamp(next_auto_attach)
            next_auto_attach_label.set_markup(_('<b>Next System Auto Attach:</b> %s') %
                next_auto_attach.strftime("%c"))
            next_auto_attach_label.show()
        else:
            next_auto_attach_label.hide()

    def _rhsmcertd_on(self):
        fnull = open(os.devnull, "w")
        try:
            # if status == 0 then true

            return not subprocess.call(['pidof', 'rhsmcertd'],
                                       stdout=fnull,
                                       stderr=fnull)
        finally:
            fnull.close()
