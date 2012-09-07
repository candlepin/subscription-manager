#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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

import base64
import os
import sys
from rhsm import certificate, _certificate
from rhsm.certificate2 import EntitlementCertificate
from rct.printing import printc, type_to_string

import gettext
from subscription_manager.cli import AbstractCLICommand, InvalidCLIOptionError
_ = gettext.gettext


class RCTCliCommand(AbstractCLICommand):
    FILE_ARG_IDX = 0

    def __init__(self, name="cli", aliases=[], shortdesc=None, primary=False):
        AbstractCLICommand.__init__(self, name=name, aliases=aliases,
                shortdesc=shortdesc, primary=primary)

    def main(self, args=None):
        # In testing we sometimes specify args, otherwise use the default:
        if args is None:
            # Skip the program name and the command name.
            args = sys.argv[2:]

        (self.options, self.args) = self.parser.parse_args(args)

        self._validate_options()
        return_code = self._do_command()
        if return_code is not None:
            return return_code

    def _validate_options(self):
        cert_file = self._get_file_from_args()
        if not cert_file:
            raise InvalidCLIOptionError(_("You must specify a certificate file."))

        if not os.path.isfile(cert_file):
            raise InvalidCLIOptionError(_("The specified certificate file does not exist."))

    def _create_cert(self):
        return certificate.create_from_file(self._get_file_from_args())

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] CERT_FILE") % self.name

    def _get_file_from_args(self):
        if not len(self.args) > self.FILE_ARG_IDX:
            return ''
        return self.args[self.FILE_ARG_IDX]


class CatCertCommand(RCTCliCommand):

    def __init__(self):
        RCTCliCommand.__init__(self, name="cat-cert", aliases=['cc'],
                               shortdesc=_("Print certificate info to standard output."),
                               primary=True)

        self.parser.add_option("--no-products", dest="no_products", action="store_true",
                               help=_("do not show the cert's product information"))
        self.parser.add_option("--no-content", dest="no_content", action="store_true",
                               help=_("do not show the cert's content info."))

    def _do_command(self):
        """
        Does the work that this command intends.
        """
        cert = self._create_cert()
        printc(cert, skip_content=self.options.no_content,
               skip_products=self.options.no_products)


class StatCertCommand(RCTCliCommand):

    def __init__(self):
        RCTCliCommand.__init__(self, name="stat-cert", aliases=['sc'],
                               shortdesc=_("Print certificate statistics and sizes."),
                               primary=True)

    def _do_command(self):
        cert = self._create_cert()
        pem = self._get_pem(self._get_file_from_args())
        print _("Type: %s" % type_to_string(cert))
        print _("Version: %s" % cert.version)
        print _("DER size: %db" % self._get_der_size(pem))

        subject_key_id = self._get_subject_key_id(pem)
        if subject_key_id is not None:
            print _("Subject Key ID size: %db" % len(subject_key_id))

        if isinstance(cert, EntitlementCertificate):
            print _("Content sets: %s" % len(cert.content))

    def _get_pem(self, filename):
        return open(filename, 'r',).read()

    def _get_der_size(self, pem):
        parts = pem.split("-----BEGIN CERTIFICATE-----\n")
        cert = parts[1].split("-----END CERTIFICATE-----")[0]
        return len(base64.b64decode(cert))

    def _get_subject_key_id(self, pem):
        cert = _certificate.load(pem=pem)
        subject_key_id = cert.get_extension(oid="2.5.29.14")
        return subject_key_id
