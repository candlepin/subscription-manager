#
# Subscription manager command line utility.
#
# Copyright (c) 2021 Red Hat, Inc.
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
import os

from subscription_manager import managerlib, rhelentbranding
from subscription_manager.i18n import ugettext as _
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.cli import system_exit

log = logging.getLogger(__name__)


class ImportCertCommand(CliCommand):
    def __init__(self):
        shortdesc = _(
            "Deprecated, this command will be removed from the future major releases."
            " This command is no-op in simple content access mode."
            " Import certificates which were provided outside of the tool"
        )
        super(ImportCertCommand, self).__init__("import", shortdesc, False)

        self.parser.add_argument(
            "--certificate",
            action="append",
            dest="certificate_file",
            help=_("certificate file to import (can be specified more than once)"),
        )

    def _validate_options(self):
        if self.is_registered():
            system_exit(
                os.EX_USAGE,
                _(
                    "Error: You may not import certificates into a system that "
                    "is registered to a subscription management service."
                ),
            )
        if not self.options.certificate_file:
            system_exit(
                os.EX_USAGE,
                _("Error: This command requires that you specify a certificate with --certificate."),
            )

    def _do_command(self):
        self._validate_options()
        # Return code
        imported_certs = []
        for src_cert_file in self.options.certificate_file:
            src_cert_file = os.path.expanduser(src_cert_file)
            if os.path.exists(src_cert_file):
                try:
                    extractor = managerlib.ImportFileExtractor(src_cert_file)

                    # Verify the entitlement data.
                    if extractor.verify_valid_entitlement():
                        extractor.write_to_disk()
                        print(
                            _("Successfully imported certificate {file}").format(
                                file=os.path.basename(src_cert_file)
                            )
                        )
                        imported_certs.append(extractor.get_cert())
                    else:
                        log.error(
                            "Error parsing manually imported entitlement "
                            "certificate: {src_cert_file}".format(src_cert_file=src_cert_file)
                        )
                        print(
                            _(
                                "{file} is not a valid certificate file. Please use a valid certificate."
                            ).format(file=os.path.basename(src_cert_file))
                        )

                except Exception as e:
                    # Should not get here unless something really bad happened.
                    log.exception(e)
                    print(
                        _(
                            "An error occurred while importing the certificate. "
                            "Please check log file for more information."
                        )
                    )
            else:
                log.error("Supplied certificate file does not exist: {file}".format(file=src_cert_file))
                print(_("{file}: file not found.").format(file=os.path.basename(src_cert_file)))

        # update branding info for the imported certs, if needed
        if imported_certs:
            # RHELBrandsInstaller will load ent dir by default
            brands_installer = rhelentbranding.RHELBrandsInstaller()
            brands_installer.install()

        self._request_validity_check()

        return_code = 0
        if not imported_certs:
            return_code = 1

        return return_code

    def require_connection(self):
        return False
