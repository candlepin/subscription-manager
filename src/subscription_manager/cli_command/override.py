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
import os

import rhsm.connection as connection

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.i18n import ugettext as _
from subscription_manager.overrides import Overrides, Override
from subscription_manager.printing_utils import columnize, echo_columnize_callback
from subscription_manager.repofile import manage_repos_enabled
from subscription_manager.utils import get_supported_resources


class OverrideCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Manage custom content repository settings")
        super(OverrideCommand, self).__init__("repo-override", shortdesc, False)
        self.parser.add_argument(
            "--repo",
            dest="repos",
            action="append",
            metavar="REPOID",
            help=_("repository to modify (can be specified more than once)"),
        )
        self.parser.add_argument(
            "--remove",
            dest="removals",
            action="append",
            metavar="NAME",
            help=_(
                "name of the override to remove (can be specified more than once); used with --repo option."
            ),
        )
        self.parser.add_argument(
            "--add",
            dest="additions",
            action="append",
            metavar="NAME:VALUE",
            help=_(
                "name and value of the option to override separated by a colon "
                "(can be specified more than once); used with --repo option."
            ),
        )
        self.parser.add_argument(
            "--remove-all",
            action="store_true",
            help=_("remove all overrides; can be specific to a repository by providing --repo"),
        )
        self.parser.add_argument(
            "--list",
            action="store_true",
            help=_("list all overrides; can be specific to a repository by providing --repo"),
        )

    def _additions_colon_split(self):
        additions = {}
        for value in self.options.additions or {}:
            if value.strip() == "":
                system_exit(
                    os.EX_USAGE, _('You must specify an override in the form of "name:value" with --add.')
                )

            k, _colon, v = value.partition(":")
            if not v or not k:
                system_exit(os.EX_USAGE, _('--add arguments should be in the form of "name:value"'))

            additions[k] = v
        self.options.additions = additions

    def _validate_options(self):
        if self.options.additions:
            self._additions_colon_split()
        if self.options.additions or self.options.removals:
            if not self.options.repos:
                system_exit(os.EX_USAGE, _("Error: You must specify a repository to modify"))
            if self.options.remove_all or self.options.list:
                system_exit(
                    os.EX_USAGE, _("Error: You may not use --add or --remove with --remove-all and --list")
                )
        if self.options.list and self.options.remove_all:
            system_exit(os.EX_USAGE, _("Error: You may not use --list with --remove-all"))
        if self.options.repos and not (
            self.options.list or self.options.additions or self.options.removals or self.options.remove_all
        ):
            system_exit(
                os.EX_USAGE, _("Error: The --repo option must be used with --list or --add or --remove.")
            )
        if self.options.removals:
            stripped_removals = [removal.strip() for removal in self.options.removals]
            if "" in stripped_removals:
                system_exit(os.EX_USAGE, _("Error: You must specify an override name with --remove."))
        # If no relevant options were given, just show a list
        if not (
            self.options.repos
            or self.options.additions
            or self.options.removals
            or self.options.remove_all
            or self.options.list
        ):
            self.options.list = True

    def _do_command(self):
        self._validate_options()
        # Abort if not registered
        self.assert_should_be_registered()

        supported_resources = get_supported_resources()
        if "content_overrides" not in supported_resources:
            system_exit(
                os.EX_UNAVAILABLE, _("Error: The 'repo-override' command is not supported by the server.")
            )

        # update entitlement certificates if necessary. If we do have new entitlements
        # CertLib.update() will call RepoActionInvoker.update().
        self.entcertlib.update()
        # make sure the EntitlementDirectory singleton is refreshed
        self._request_validity_check()

        overrides = Overrides()

        if not manage_repos_enabled():
            print(_("Repositories disabled by configuration."))

        if self.options.list:
            results = overrides.get_overrides(self.identity.uuid)
            if results:
                self._list(results, self.options.repos)
            else:
                print(_("This system does not have any content overrides applied to it."))
            return

        if self.options.additions:
            repo_ids = [repo.id for repo in overrides.repo_lib.get_repos(apply_overrides=False)]
            to_add = [
                Override(repo, name, value)
                for repo in self.options.repos
                for name, value in list(self.options.additions.items())
            ]
            try:
                results = overrides.add_overrides(self.identity.uuid, to_add)
            except connection.RestlibException as ex:
                if ex.code == 400:
                    # blocklisted overrides specified.
                    # Print message and return a less severe code.
                    system_exit(1, ex)
                else:
                    raise ex

            # Print out warning messages if the specified repo does not exist in the repo file.
            for repo in self.options.repos:
                if repo not in repo_ids:
                    print(
                        _(
                            "Repository '{repo}' does not currently exist, but the override has been added."
                        ).format(repo=repo)
                    )

        if self.options.removals:
            to_remove = [
                Override(repo, item) for repo in self.options.repos for item in self.options.removals
            ]
            results = overrides.remove_overrides(self.identity.uuid, to_remove)
        if self.options.remove_all:
            results = overrides.remove_all_overrides(self.identity.uuid, self.options.repos)

        # Update the cache and refresh the repo file.
        overrides.update(results)

    def _list(self, all_overrides, specific_repos):
        overrides = {}
        for override in all_overrides:
            repo = override.repo_id
            name = override.name
            value = override.value
            # overrides is a hash of hashes.  Like this: {'repo_x': {'enabled': '1', 'gpgcheck': '1'}}
            overrides.setdefault(repo, {})[name] = value

        to_show = set(overrides.keys())
        if specific_repos:
            specific_repos = set(specific_repos)
            for r in specific_repos.difference(to_show):
                print(_("Nothing is known about '{r}'").format(r=r))
            # Take the intersection of the sets
            to_show &= specific_repos

        for repo in sorted(to_show):
            print(_("Repository: {repo}").format(repo=repo))
            repo_data = sorted(list(overrides[repo].items()), key=lambda x: x[0])
            # Split the list of 2-tuples into a list of names and a list of keys
            names, values = list(zip(*repo_data))
            names = ["{x}:".format(x=x) for x in names]
            print(columnize(names, echo_columnize_callback, *values, indent=2) + "\n")
