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
from subscription_manager.i18n import ugettext as _
from subscription_manager.cli_command.abstract_syspurpose import AbstractSyspurposeCommand
from subscription_manager.cli_command.org import OrgCommand


class AddonsCommand(AbstractSyspurposeCommand, OrgCommand):
    def __init__(self, subparser=None):
        shortdesc = _(
            "Deprecated, this command will be removed from the future major releases."
            " This command is no-op."
            " Show or modify the system purpose addons setting"
        )
        super(AddonsCommand, self).__init__(
            "addons",
            subparser,
            shortdesc=shortdesc,
            primary=False,
            attr="addons",
            commands=["unset", "add", "remove", "show", "list"],
        )
