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
import subscription_manager.injection as inj

from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _


class AutohealCommand(CliCommand):
    def __init__(self):
        self.uuid = inj.require(inj.IDENTITY).uuid

        shortdesc = _(
            "Deprecated, this option will be removed from the future major releases. "
            "Set if subscriptions are attached on a schedule (default of daily)"
        )
        self._org_help_text = _("specify whether to enable or disable auto-attaching of subscriptions")
        super(AutohealCommand, self).__init__("auto-attach", shortdesc, False)

        self.parser.add_argument(
            "--enable",
            dest="enable",
            action="store_true",
            help=_("try to attach subscriptions for uncovered products each check-in"),
        )
        self.parser.add_argument(
            "--disable",
            dest="disable",
            action="store_true",
            help=_("do not try to automatically attach subscriptions each check-in"),
        )
        self.parser.add_argument(
            "--show",
            dest="show",
            action="store_true",
            help=_("show the current auto-attach preference"),
        )

    def _toggle(self, autoheal):
        self.cp.updateConsumer(self.uuid, autoheal=autoheal)
        self._show(autoheal)

    def _validate_options(self):
        if not self.uuid:
            self.assert_should_be_registered()

    def _show(self, autoheal):
        if autoheal:
            print(_("Auto-attach preference: enabled"))
        else:
            print(_("Auto-attach preference: disabled"))

    def _do_command(self):
        self._validate_options()

        if not self.options.enable and not self.options.disable:
            self._show(self.cp.getConsumer(self.uuid)["autoheal"])
        else:
            self._toggle(self.options.enable or False)
