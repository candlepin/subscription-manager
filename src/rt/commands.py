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

import os
from rhsm import certificate
from rt.cli import CLICommand, InvalidCLIOptionError
from rt.printing import printc

import gettext
_ = gettext.gettext


class CatCertCommand(CLICommand):
    FILE_ARG_IDX = 0

    def __init__(self):
        CLICommand.__init__(self, "cc", _("Show certificate info."))

    def _define_custom_opts(self, parser):
        self.parser.add_option("--no-products", dest="no_products", action="store_true",
                               help=_("do not show the cert's product information"))
        self.parser.add_option("--no-content", dest="no_content", action="store_true",
                               help=_("do not show the cert's content info."))

    def _validate_options(self):
        cert_file = self._get_file_from_args()
        if not cert_file:
            raise InvalidCLIOptionError(_("You must specify a certificate file."))

        if not os.path.isfile(cert_file):
            raise InvalidCLIOptionError(_("The specified certificate file does not exist."))

    def _run_command(self):
        """
        Does the work that this command intends.
        """
        cert = self._create_cert()
        printc(cert, skip_content=self.options.no_content,
               skip_products=self.options.no_products)

    def _create_cert(self):
        return certificate.create_from_file(self._get_file_from_args())

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] CERT_FILE") % self.name

    def _get_file_from_args(self):
        if not len(self.args) > self.FILE_ARG_IDX:
            return ''
        return self.args[self.FILE_ARG_IDX]
