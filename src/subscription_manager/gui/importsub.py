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
import os
import logging
import gtk

_ = gettext.gettext

from subscription_manager.managerlib import ImportFileExtractor
from subscription_manager.gui import widgets, messageWindow
from subscription_manager.gui.utils import errorWindow

log = logging.getLogger('rhsm-app.' + __name__)


class ImportSubDialog(object):
    """
    Dialog to manually import an entitlement certificate for this machine.
    Generally used for disconnected (unregistered) systems.
    """
    def __init__(self):
        self._parent = None

        self.dialog = gtk.FileChooserDialog(_("Import Certificates"),
                None, gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                 _("Import"), gtk.RESPONSE_OK))
        self.dialog.set_default_response(gtk.RESPONSE_OK)
        self.dialog.set_modal(True)

        self.dialog.set_local_only(True)
        self.dialog.set_select_multiple(True)

        afilter = gtk.FileFilter()
        afilter.set_name(_("Certificates"))
        afilter.add_pattern("*.pem")
        self.dialog.add_filter(afilter)

        afilter = gtk.FileFilter()
        afilter.set_name(_("All files"))
        afilter.add_pattern("*")
        self.dialog.add_filter(afilter)

        self.dialog.connect("response", self._on_dialog_response)

    def _on_dialog_response(self, dialog, response_id):
        if response_id == gtk.RESPONSE_CANCEL:
            return self._cancel_button_clicked()
        elif response_id == gtk.RESPONSE_OK:
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

        for cert_file in src_cert_files:
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
            except Exception, e:
                # Should not get here unless something really bad happened.
                log.exception(e)
                error_certs.append(cert_file)

        if len(error_certs) > 0 or len(invalid_certs) > 0:
            msg = ""
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
            errorWindow(msg, parent=self._parent)
        else:
            #if we get to this point, the import was successful
            messageWindow.InfoDialog(_("Certificate import was successful."),
                    parent=self._parent)
        self.dialog.hide()
        self.dialog.unselect_all()

    def set_parent_window(self, window):
        self._parent = window
        self.dialog.set_transient_for(window)
