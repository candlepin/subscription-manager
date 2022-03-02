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
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _

SM = "subscription-manager"


class PluginsCommand(CliCommand):
    def __init__(self):
        shortdesc = _("View and configure with 'subscription-manager plugins'")
        super(PluginsCommand, self).__init__("plugins", shortdesc, False)

        self.parser.add_argument(
            "--list",
            action="store_true",
            help=_("list {SM} plugins").format(SM=SM),
        )
        self.parser.add_argument(
            "--listslots", action="store_true", help=_("list {SM} plugin slots").format(SM=SM)
        )
        self.parser.add_argument(
            "--listhooks", action="store_true", help=_("list {SM} plugin hooks").format(SM=SM)
        )
        self.parser.add_argument(
            "--verbose", action="store_true", default=False, help=_("show verbose plugin info")
        )

    def _validate_options(self):
        # default to list
        if not (self.options.list or self.options.listslots or self.options.listhooks):
            self.options.list = True

    def require_connection(self):
        return False

    def _list_plugins(self):
        for plugin_class in list(self.plugin_manager.get_plugins().values()):
            enabled = _("disabled")
            if plugin_class.conf.is_plugin_enabled():
                enabled = _("enabled")
            print("{key}: {enabled}".format(key=plugin_class.get_plugin_key(), enabled=enabled))
            if self.options.verbose:
                print(plugin_class.conf)

    def _do_command(self):
        self._validate_options()

        if self.options.list:
            self._list_plugins()

        if self.options.listslots:
            for slot in self.plugin_manager.get_slots():
                print(slot)

        if self.options.listhooks:
            # get_slots is nicely sorted for presentation
            for slot in self.plugin_manager.get_slots():
                print(slot)
                for hook in sorted(self.plugin_manager._slot_to_funcs[slot], key=lambda func: func.__name__):
                    hook_key = hook.__self__.__class__.get_plugin_key()
                    print("\t{key}.{name}".format(key=hook_key, name=hook.__name__))
