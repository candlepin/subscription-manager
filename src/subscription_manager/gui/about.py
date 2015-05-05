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
import gettext
import os
import subprocess

#from gi.repository import Gtk
from gi.repository import Gtk

from subscription_manager.gui.utils import get_running_as_firstboot
from subscription_manager.utils import get_client_versions, get_server_versions

_ = gettext.gettext

LICENSE = _("\nThis software is licensed to you under the GNU General Public License, "
            "version 2 (GPLv2). There is NO WARRANTY for this software, express or "
            "implied, including the implied warranties of MERCHANTABILITY or FITNESS "
            "FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2 "
            "along with this software; if not, see:\n\n"
            "http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt\n\n"
            "Red Hat trademarks are not licensed under GPLv2. No permission is "
            "granted to use or replicate Red Hat trademarks that are incorporated "
            "in this software or its documentation.\n")

UPDATE_FILE = '/var/run/rhsm/update'

prefix = os.path.dirname(__file__)


class AboutDialog(object):
    def __init__(self, parent, backend):
        self.backend = backend
        self.dialog = Gtk.AboutDialog()
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

        next_update_label = Gtk.Label()
        python_rhsm_version_label = Gtk.Label()
        sub_man_version_label = Gtk.Label()
        backend_version_label = Gtk.Label()
        context_box = self.dialog.vbox.get_children()[0]
        context_box.pack_end(next_update_label, True, True, 0)
        context_box.pack_end(python_rhsm_version_label, True, True, 0)
        context_box.pack_end(sub_man_version_label, True, True, 0)
        context_box.pack_end(backend_version_label, True, True, 0)

        self._set_next_update(next_update_label)

        # Set the component versions.
        server_versions = get_server_versions(self.backend.cp_provider.get_consumer_auth_cp())
        client_versions = get_client_versions()

        python_rhsm_version_label.set_markup(_("<b>%s version:</b> %s") %
                                        ("python-rhsm", client_versions['python-rhsm']))
        sub_man_version_label.set_markup(_("<b>%s version:</b> %s") %
                                        ("subscription manager", client_versions['subscription-manager']))
        backend_version_label.set_markup(_("<b>subscription management service version:</b> %s") %
                                           server_versions['candlepin'])

        self.dialog.connect("response", self._handle_response)
        self.dialog.show_all()

    def show(self):
        self.dialog.show()

    def _handle_response(self, dialog, response):
        if response == Gtk.ResponseType.DELETE_EVENT or response == Gtk.ResponseType.CANCEL:
            self.dialog.destroy()

    def _set_next_update(self, next_update_label):
        try:
            if self._rhsmcertd_on():
                next_update = long(file(UPDATE_FILE).read())
            else:
                next_update = None
        except Exception:
            next_update = None

        if next_update:
            update_time = datetime.datetime.fromtimestamp(next_update)
            next_update_label.set_markup(_('<b>Next System Check-in:</b> %s') %
                update_time.strftime("%c"))
            next_update_label.show()
        else:
            next_update_label.hide()

    def _rhsmcertd_on(self):
        fnull = open(os.devnull, "w")
        try:
            # if status == 0 then true

            return not subprocess.call(['pidof', 'rhsmcertd'],
                                       stdout=fnull,
                                       stderr=fnull)
        finally:
            fnull.close()
