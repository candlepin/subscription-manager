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

import os
from gtk import gdk, RESPONSE_DELETE_EVENT, RESPONSE_CANCEL, \
                AboutDialog as GtkAboutDialog, Label
from rhsm.version import Versions
from subscription_manager.utils import get_version

import gettext
_ = gettext.gettext

LICENSE = _("\nThis software is licensed to you under the GNU General Public License, " \
            "version 2 (GPLv2). There is NO WARRANTY for this software, express or " \
            "implied, including the implied warranties of MERCHANTABILITY or FITNESS " \
            "FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2 " \
            "along with this software; if not, see:\n\n" \
            "http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt\n\n" \
            "Red Hat trademarks are not licensed under GPLv2. No permission is " \
            "granted to use or replicate Red Hat trademarks that are incorporated " \
            "in this software or its documentation.\n")

prefix = os.path.dirname(__file__)
LOGO_PATH = os.path.join(prefix, "data/icons/scalable/subscription-manager.svg")


class AboutDialog(object):
    def __init__(self, parent):
        self.dialog = GtkAboutDialog()
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.dialog.set_program_name(_("Subscription Manager"))
        self.dialog.set_license(LICENSE)
        self.dialog.set_wrap_license(True)
        self.dialog.set_website("https://fedorahosted.org/subscription-manager/")
        self.dialog.set_copyright(_("Copyright (c) 2012 Red Hat, Inc."))
        self.dialog.set_logo(gdk.pixbuf_new_from_file_at_size(LOGO_PATH, 100, 100))

        rhsm_version_label = Label()
        context_box = self.dialog.get_content_area().get_children()[0]
        context_box.pack_end(rhsm_version_label)

        # Set the component versions.
        versions = Versions()
        self.dialog.set_version(get_version(versions, Versions.SUBSCRIPTION_MANAGER))
        rhsm_version = get_version(versions, Versions.PYTHON_RHSM)
        rhsm_version_label.set_markup(_("<b>python-rhsm version:</b> %s" % rhsm_version))

        self.dialog.connect("response", self._handle_response)
        self.dialog.show_all()

    def show(self):
        self.dialog.show()

    def _handle_response(self, dialog, response):
        if response == RESPONSE_DELETE_EVENT or response == RESPONSE_CANCEL:
            self.dialog.destroy()
