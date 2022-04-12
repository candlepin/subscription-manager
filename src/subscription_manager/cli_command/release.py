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

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, conf
from subscription_manager.i18n import ugettext as _
from subscription_manager.release import ReleaseBackend, MultipleReleaseProductsError
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.utils import parse_baseurl_info
import subscription_manager.injection as inj

log = logging.getLogger(__name__)


class ReleaseCommand(CliCommand):
    def __init__(self):
        shortdesc = _("Configure which operating system release to use")
        super(ReleaseCommand, self).__init__("release", shortdesc, True)

        self.parser.add_argument(
            "--show",
            dest="show",
            action="store_true",
            help=_("shows current release setting; default command"),
        )
        self.parser.add_argument(
            "--list",
            dest="list",
            action="store_true",
            help=_("list available releases"),
        )
        self.parser.add_argument(
            "--set",
            dest="release",
            action="store",
            default=None,
            help=_("set the release for this system"),
        )
        self.parser.add_argument(
            "--unset",
            dest="unset",
            action="store_true",
            help=_("unset the release for this system"),
        )

    def _get_consumer_release(self):
        err_msg = _("Error: The 'release' command is not supported by the server.")
        consumer = self.cp.getConsumer(self.identity.uuid)
        if "releaseVer" not in consumer:
            system_exit(os.EX_UNAVAILABLE, err_msg)
        return consumer["releaseVer"]["releaseVer"]

    def show_current_release(self):
        release = self._get_consumer_release()
        if release:
            print(_("Release: {release}").format(release=release))
        else:
            print(_("Release not set"))

    def _do_command(self):
        cdn_url = conf["rhsm"]["baseurl"]
        # note: parse_baseurl_info will populate with defaults if not found
        (cdn_hostname, cdn_port, _cdn_prefix) = parse_baseurl_info(cdn_url)

        # Base CliCommand has already setup proxy info etc
        self.cp_provider.set_content_connection_info(cdn_hostname=cdn_hostname, cdn_port=cdn_port)
        self.release_backend = ReleaseBackend()

        self.assert_should_be_registered()

        repo_action_invoker = RepoActionInvoker()

        if self.options.unset:
            self.cp.updateConsumer(self.identity.uuid, release="")
            inj.require(inj.RELEASE_STATUS_CACHE).delete_cache()
            repo_action_invoker.update()
            print(_("Release preference has been unset"))
        elif self.options.release is not None:
            # get first list of available releases from the server
            try:
                releases = self.release_backend.get_releases()
            except MultipleReleaseProductsError as err:
                log.error("Getting releases failed: {err}".format(err=err))
                system_exit(os.EX_CONFIG, err.translated_message())

            if self.options.release in releases:
                self.cp.updateConsumer(self.identity.uuid, release=self.options.release)
            else:
                system_exit(
                    os.EX_DATAERR,
                    _(
                        "No releases match '{release}'.  " "Consult 'release --list' for a full listing."
                    ).format(release=self.options.release),
                )
            inj.require(inj.RELEASE_STATUS_CACHE).delete_cache()
            repo_action_invoker.update()
            print(_("Release set to: {release}").format(release=self.options.release))
        elif self.options.list:
            try:
                releases = self.release_backend.get_releases()
            except MultipleReleaseProductsError as err:
                log.error("Getting releases failed: {err}".format(err=err))
                system_exit(os.EX_CONFIG, err.translated_message())

            if len(releases) == 0:
                system_exit(os.EX_CONFIG, _("No release versions available, please check subscriptions."))

            print("+-------------------------------------------+")
            print("          {label}       ".format(label=_("Available Releases")))
            print("+-------------------------------------------+")
            for release in releases:
                print(release)

        else:
            self.show_current_release()
