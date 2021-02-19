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
import fnmatch
import logging
import subscription_manager.injection as inj

from subscription_manager.action_client import ProfileActionClient, ActionClient
from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.cli_command.list import REPOS_LIST
from subscription_manager.i18n import ugettext as _
from subscription_manager.packageprofilelib import PackageProfileActionInvoker
from subscription_manager.printing_utils import columnize, echo_columnize_callback
from subscription_manager.repofile import manage_repos_enabled, YumRepoFile
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.utils import get_supported_resources

log = logging.getLogger(__name__)


class ReposCommand(CliCommand):

    def __init__(self):
        shortdesc = _("List the repositories which this system is entitled to use")
        super(ReposCommand, self).__init__("repos", shortdesc, False)

        def repo_callback(option, opt, repoid, parser):
            """
            Store our repos to enable and disable in a combined, ordered list of
            tuples. (enabled, repoid)

            This allows us to have our expected behaviour when we do things like
            --disable="*" --enable="1" --enable="2".
            """
            status = '0'
            if opt == '--enable':
                status = '1'
            vars(parser.values).setdefault('repo_actions',
                                           []).append((status, repoid))

        def list_callback(option, opt, repoid, parser):
            """
            Handles setting both enabled/disabled filter options when the --list argument is
            provided.

            Allows for --list to perform identically to --list-enabled --list-disabled
            """
            parser.values.list = True

            if opt in ("--list", "--list-enabled"):
                parser.values.list_enabled = True

            if opt in ("--list", "--list-disabled"):
                parser.values.list_disabled = True

        self.parser.add_option("--list",
                               action="callback", callback=list_callback, dest="list", default=False,
                               help=_("list all known repositories for this system"))
        self.parser.add_option("--list-enabled",
                               action="callback", callback=list_callback, dest="list_enabled", default=False,
                               help=_("list known, enabled repositories for this system"))
        self.parser.add_option("--list-disabled",
                               action="callback", callback=list_callback, dest="list_disabled", default=False,
                               help=_("list known, disabled repositories for this system"))
        self.parser.add_option("--enable", dest="enable", type="str",
                               action='callback', callback=repo_callback, metavar="REPOID",
                               help=_(
                                   "repository to enable (can be specified more than once). Wildcards (* and ?) are supported."))
        self.parser.add_option("--disable", dest="disable", type="str",
                               action='callback', callback=repo_callback, metavar="REPOID",
                               help=_(
                                   "repository to disable (can be specified more than once). Wildcards (* and ?) are supported."))

    def _validate_options(self):
        if not (self.options.list or hasattr(self.options, 'repo_actions')):
            self.options.list = True
            self.options.list_enabled = True
            self.options.list_disabled = True

    def _do_command(self):
        self._validate_options()
        rc = 0
        if not manage_repos_enabled():
            print(_("Repositories disabled by configuration."))
            return rc

        # Pull down any new entitlements and refresh the entitlements directory
        if self.identity.is_valid():
            cert_action_client = ActionClient(skips=[PackageProfileActionInvoker])
            cert_action_client.update()
            self._request_validity_check()

        if self.is_registered():
            supported_resources = get_supported_resources()
            self.use_overrides = 'content_overrides' in supported_resources
        else:
            self.use_overrides = False

        # specifically, yum repos, for now.
        rl = RepoActionInvoker()
        repos = rl.get_repos()

        if hasattr(self.options, 'repo_actions'):
            rc = self._set_repo_status(repos, rl, self.options.repo_actions)

        if self.identity.is_valid():
            profile_action_client = ProfileActionClient()
            profile_action_client.update()

        if self.options.list:
            if len(repos):
                # TODO: Perhaps this should be abstracted out as well...?
                def filter_repos(repo):
                    disabled_values = ['false', '0']
                    repo_enabled = repo['enabled'].lower()
                    show_enabled = (self.options.list_enabled and repo_enabled not in disabled_values)
                    show_disabled = (self.options.list_disabled and repo_enabled in disabled_values)

                    return show_enabled or show_disabled

                repos = list(filter(filter_repos, repos))

                if len(repos):
                    print("+----------------------------------------------------------+")
                    print(_("    Available Repositories in {file}").format(file=rl.get_repo_file()))
                    print("+----------------------------------------------------------+")

                    for repo in repos:
                        print(columnize(REPOS_LIST, echo_columnize_callback,
                                        repo.id,
                                        repo["name"],
                                        repo["baseurl"],
                                        repo["enabled"]) + "\n")
                else:
                    print(_("There were no available repositories matching the specified criteria."))
            else:
                print(_("This system has no repositories available through subscriptions."))

        return rc

    def _set_repo_status(self, repos, repo_action_invoker, repo_actions):
        """
        Given a list of repo actions (tuple of enable/disable and
        repo ID), build the master list (without duplicates) to send to the
        server.
        """
        rc = 0

        # Maintain a dict of repo to enabled/disabled status. This allows us
        # to remove dupes and send only the last action specified by the user
        # on the command line. Items will be overwritten as we process the CLI
        # arguments in order.
        repos_to_modify = {}

        if not len(repos):
            print(_("This system has no repositories available through subscriptions."))
            return 1

        for (status, repoid) in repo_actions:
            matches = set([repo for repo in repos if fnmatch.fnmatch(repo.id, repoid)])
            if not matches:
                rc = 1
                print(_("Error: '{repoid}' does not match a valid repository ID. "
                        "Use \"subscription-manager repos --list\" to see valid repositories.").format(repoid=repoid))
                log.warning("'{repoid}' does not match a valid repository ID.".format(repoid=repoid))

            # Overwrite repo if it's already in the dict, we want the last
            # match to be the one sent to server.
            for repo in matches:
                repos_to_modify[repo] = status

        if repos_to_modify:
            # The cache should be primed at this point by the
            # repo_action_invoker.get_repos()
            cache = inj.require(inj.OVERRIDE_STATUS_CACHE)

            if self.is_registered() and self.use_overrides:
                overrides = [{'contentLabel': repo.id, 'name': 'enabled', 'value': repos_to_modify[repo]} for repo in
                             repos_to_modify]
                metadata_overrides = [
                    {'contentLabel': repo.id, 'name': 'enabled_metadata', 'value': repos_to_modify[repo]} for repo in
                    repos_to_modify]
                overrides.extend(metadata_overrides)
                results = self.cp.setContentOverrides(self.identity.uuid, overrides)

                cache = inj.require(inj.OVERRIDE_STATUS_CACHE)

                # Update the cache with the returned JSON
                cache.server_status = results
                cache.write_cache()

                repo_action_invoker.update()
            else:
                # When subscription-manager is in offline mode, then we have to generate redhat.repo from
                # entitlement certificates
                rl = RepoActionInvoker()
                rl.update()
                # In the disconnected case we must modify the repo file directly.
                changed_repos = [repo for repo in matches if repo['enabled'] != status]
                for repo in changed_repos:
                    repo['enabled'] = status
                    repo['enabled_metadata'] = status
                if changed_repos:
                    repo_file = YumRepoFile()
                    repo_file.read()
                    for repo in changed_repos:
                        repo_file.update(repo)
                    repo_file.write()

        for repo in repos_to_modify:
            # Watchout for string comparison here:
            if repos_to_modify[repo] == "1":
                print(_("Repository '{repoid}' is enabled for this system.").format(repoid=repo.id))
            else:
                print(_("Repository '{repoid}' is disabled for this system.").format(repoid=repo.id))
        return rc
