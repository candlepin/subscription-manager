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
import re

_ = gettext.gettext

import rhsm.config

from subscription_manager.gui import widgets
from subscription_manager.gui.utils import errorWindow

from rhsm.certificate import EntitlementCertificate

cfg = rhsm.config.initConfig()
ENT_CONFIG_DIR = cfg.get('rhsm', 'entitlementCertDir')

log = logging.getLogger('rhsm-app.' + __name__)


class ImportSubDialog(widgets.GladeWidget):
    """
    Dialog to manually import an entitlement certificate for this machine.
    Generally used for disconnected (unregistered) systems.
    """
    def __init__(self):

        widget_names = [
                'main_dialog',
                'certificate_chooser_button',
        ]
        super(ImportSubDialog, self).__init__('importsub.glade', widget_names)

        dic = {
                "on_import_cancel_button_clicked": self._cancel_button_clicked,
                "on_certificate_import_button_clicked": self._import_button_clicked,
            }
        self.glade.signal_autoconnect(dic)

        self.main_dialog.connect("hide", self._cancel_button_clicked)
        self.main_dialog.connect("delete_event", self._delete_event)

    def _cancel_button_clicked(self, button=None):
        self.main_dialog.hide()
        return True

    def show(self):
        self.main_dialog.present()

    def _delete_event(self, event, data=None):
        return self._cancel_button_clicked()

    def _import_button_clicked(self, button):
        src_cert_file = self.certificate_chooser_button.get_filename()
        if src_cert_file is None:
            errorWindow(_("You must select a certificate."))
            return False

        # Check to see if we have a key included in the cert file
        try:
            extractor = ImportFileExtractor(src_cert_file)

            #Verify the entitlement data.
            if not extractor.verify_valid_entitlement():
                log.error("Invalid X509 entitlement certificate.")
                log.error("Error parsing manually imported entitlement "
                    "certificate: %s" % src_cert_file)
                errorWindow(_("%s is not a valid certificate file. Please upload a valid certificate.") %
                            os.path.basename(src_cert_file))
                return False

            extractor.write_to_disk()
        except Exception, e:
            # Should not get here unless something really bad happened.
            log.exception(e)
            errorWindow(_("An error occurred while importing the certificate. " +
                          "Please check log file for more information."))
            return False

        self.certificate_chooser_button.unselect_all()
        self.main_dialog.hide()

    def set_parent_window(self, window):
        self.main_dialog.set_transient_for(window)

class ImportFileExtractor(object):
    """
    Responsible for checking an import file and pulling cert and key from it.
    An import file may include only the certificate, but may also include its
    key.

    An import file is processed looking for:

    -----BEGIN <TAG>-----
    <CONTENT>
    ..
    -----END <TAG>-----

    and will only process if it finds CERTIFICATE or KEY in the <TAG> text.

    For example the following would locate a key and cert.

    -----BEGIN CERTIFICATE-----
    <CERT_CONTENT>
    -----END CERTIFICATE-----
    -----BEGIN PUBLIC KEY-----
    <KEY_CONTENT>
    -----END PUBLIC KEY-----

    """
    _REGEX_START_GROUP = "start"
    _REGEX_CONTENT_GROUP = "content"
    _REGEX_END_GROUP = "end"
    _REGEX = "(?P<%s>[-]*BEGIN[\w\ ]*[-]*)(?P<%s>[^-]*)(?P<%s>[-]*END[\w\ ]*[-]*)" % \
                (_REGEX_START_GROUP, _REGEX_CONTENT_GROUP, _REGEX_END_GROUP)
    _PATTERN = re.compile(_REGEX)

    _CERT_DICT_TAG = "CERTIFICATE"
    _KEY_DICT_TAG = "KEY"

    def __init__(self, cert_file_path):
            self.path = cert_file_path
            self.file_name = os.path.basename(cert_file_path)

            content = self._read(cert_file_path)
            self.parts = self._process_content(content)

    def _read(self, file_path):
        file = open(file_path, "r")
        file_content = file.read()
        file.close()
        return file_content

    def _process_content(self, content):
        part_dict = {}
        matches = self._PATTERN.finditer(content)
        for match in matches:
            start = match.group(self._REGEX_START_GROUP)
            meat = match.group(self._REGEX_CONTENT_GROUP)
            end = match.group(self._REGEX_END_GROUP)

            dict_key = None
            if not start.find(self._KEY_DICT_TAG) < 0:
                dict_key = self._KEY_DICT_TAG
            elif not start.find(self._CERT_DICT_TAG) < 0:
                dict_key = self._CERT_DICT_TAG

            if dict_key is None:
                continue

            part_dict[dict_key] = start + meat + end
        return part_dict

    def contains_key_content(self):
        return self.parts.has_key(self._KEY_DICT_TAG)

    def get_key_content(self):
        key_content = None
        if self.parts.has_key(self._KEY_DICT_TAG):
            key_content = self.parts[self._KEY_DICT_TAG]
        return key_content

    def get_cert_content(self):
        cert_content = None
        if self.parts.has_key(self._CERT_DICT_TAG):
            cert_content = self.parts[self._CERT_DICT_TAG]
        return cert_content

    def verify_valid_entitlement(self):
        """
        Verify that a valid entitlement was processed.

        @return: True if valid, False otherwise.
        """
        ent_cert = EntitlementCertificate(self.get_cert_content())
        if ent_cert.bogus():
            return False
        return True

    def write_to_disk(self):
        """
        Write/copy cert to the entitlement cert dir.
        """
        if not os.access(ENT_CONFIG_DIR, os.R_OK):
            os.mkdir(ENT_CONFIG_DIR)

        dest_file_path = os.path.join(ENT_CONFIG_DIR, os.path.basename(self.path))

        # Write the key/cert content to new files
        log.debug("Writing certificate file: %s" % (dest_file_path))
        self._write_file(dest_file_path, self.get_cert_content())

        if self.contains_key_content():
            dest_key_file_path = self._get_key_path_from_dest_cert_path(dest_file_path)
            log.debug("Writing key file: %s" % (dest_key_file_path))
            self._write_file(dest_key_file_path, self.get_key_content())

    def _write_file(self, target_path, content):
        new_file = open(target_path, "w")
        try:
            new_file.write(content)
        finally:
            new_file.close()

    def _get_key_path_from_dest_cert_path(self, dest_cert_path):
        file_parts = os.path.splitext(dest_cert_path)
        return file_parts[0] + "-key" + file_parts[1]
