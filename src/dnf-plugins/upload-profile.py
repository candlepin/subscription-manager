from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2015 Red Hat, Inc.
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

"""
This file contains code of dnf subcommand called "upload" used for uploading of combined profile (list of rpm
packages, enabled repositories, modules).
"""


from dnfpluginscore import _, logger
import dnf.cli

from subscription_manager import packageprofilelib
from subscription_manager.injectioninit import init_dep_injection


@dnf.plugin.register_command
class UploadProfileCommand(dnf.cli.Command):
    name = "upload-profile"
    aliases = ("uploadprofile", "upload-profile",)
    summary = _("Upload combined profile to Satellite server (list of installed rpms, enabled repositories and modules")

    def __init__(self, cli):
        super(UploadProfileCommand, self).__init__(cli)

    @staticmethod
    def set_argparser(parser):
        parser.add_argument('--force-upload', action='store_true',
                            help=_('Force package profile upload'))

    def configure(self):
        pass

    def run(self):
        try:
            init_dep_injection()
        except ImportError as e:
            logger.error(str(e))
            return

        command = packageprofilelib.PackageProfileActionCommand()
        report = command.perform(force_upload=self.opts.force_upload)

        if report._status == 0:
            print(_("No updates performed. See /var/log/rhsm/rhsm.log for more information."))
        else:
            print(report)
