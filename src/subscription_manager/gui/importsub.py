#
# Copyright (c) 2010 Red Hat, Inc.
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
import os

from gi.repository import Gtk

from subscription_manager import rhelentbranding
from subscription_manager.gui import messageWindow
from subscription_manager.gui.utils import show_error_window
from subscription_manager.managerlib import ImportFileExtractor

log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


class ImportSubDialog(object):
    """
    Dialog to manually import an entitlement certificate for this machine.
    Generally used for disconnected (unregistered) systems.
    """
    def __init__(self):
        self._parent = None

        self.dialog = Gtk.FileChooserDialog(_("Import Certificates"),
                None, Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 _("Import"), Gtk.ResponseType.OK))
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        self.dialog.set_modal(True)

        self.dialog.set_local_only(True)
        self.dialog.set_select_multiple(True)
        self.dialog.set_icon_name('subscription-manager')

        afilter = Gtk.FileFilter()
        afilter.set_name(_("Certificates"))
        afilter.add_pattern("*.pem")
        self.dialog.add_filter(afilter)

        afilter = Gtk.FileFilter()
        afilter.set_name(_("All files"))
        afilter.add_pattern("*")
        self.dialog.add_filter(afilter)

        self.dialog.connect("response", self._on_dialog_response)
        self.dialog.connect("delete-event", self._delete_event)

    def _on_dialog_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.CANCEL:
            return self._cancel_button_clicked()
        elif response_id == Gtk.ResponseType.OK:
            return self._import_button_clicked()
        # other response is on dialog destroy, we don't act on that.

    def _cancel_button_clicked(self):
        self.dialog.hide()
        return True

    def show(self):
        self.dialog.present()

    def _delete_event(self, event, data=None):
        return self._cancel_button_clicked()

    def _import_button_clicked(self):
        src_cert_files = self.dialog.get_filenames()

        invalid_certs = []
        error_certs = []
        good_certs = []
        imported_certs = []
        non_cert_files = []

        for cert_file in src_cert_files:
            if not os.path.exists(cert_file):
                non_cert_files.append(cert_file)
            else:
                # Check to see if we have a key included in the cert file
                try:
                    extractor = ImportFileExtractor(cert_file)

                    #Verify the entitlement data.
                    if not extractor.verify_valid_entitlement():
                        log.error("Invalid X509 entitlement certificate.")
                        log.error("Error parsing manually imported entitlement "
                            "certificate: %s" % cert_file)
                        invalid_certs.append(cert_file)
                    else:
                        extractor.write_to_disk()
                        good_certs.append(cert_file)
                        imported_certs.append(extractor.get_cert())
                except Exception, e:
                    # Should not get here unless something really bad happened.
                    log.exception(e)
                    error_certs.append(cert_file)

        if imported_certs:
            brands_installer = rhelentbranding.RHELBrandsInstaller()
            brands_installer.install()

        if len(error_certs) > 0 \
            or len(invalid_certs) > 0 \
            or len(non_cert_files) > 0:

            msg = ""
            if len(non_cert_files) > 0:
                msg += _("The following certificate files did not exist:")
                msg += "\n" + "\n".join(non_cert_files)
            if len(invalid_certs) > 0:
                msg += _("The following files are not valid certificates and were not imported:")
                msg += "\n" + "\n".join(invalid_certs)
            if len(error_certs) > 0:
                if len(invalid_certs) > 0:
                    msg += "\n\n"
                msg += _("An error occurred while importing the following certificates. Please check the log file for more information.")
                msg += "\n" + "\n".join(error_certs)
            if len(good_certs) > 0:
                msg += "\n\n"
                msg += _("The following certificates were successfully imported:")
                msg += "\n" + "\n".join(good_certs)
            show_error_window(msg, parent=self._parent)
        else:
            #if we get to this point, the import was successful
            messageWindow.InfoDialog(_("Certificate import was successful."),
                    parent=self._parent)
        self.dialog.hide()
        self.dialog.unselect_all()

    def set_parent_window(self, window):
        self._parent = window
        self.dialog.set_transient_for(window)
