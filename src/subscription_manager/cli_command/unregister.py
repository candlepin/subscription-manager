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
from rhsmlib.services import unregister

from subscription_manager.action_client import UnregisterActionClient
from subscription_manager.branding import get_branding
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, conf, ERR_NOT_REGISTERED_CODE, handle_exception
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import restart_virt_who


class UnRegisterCommand(CliCommand):
    def __init__(self):
        shortdesc = get_branding().CLI_UNREGISTER
        super(UnRegisterCommand, self).__init__("unregister", shortdesc, True)

    def _validate_options(self):
        pass

    def _do_command(self):
        if not self.is_registered():
            # TODO: Should this use the standard NOT_REGISTERED message?
            system_exit(ERR_NOT_REGISTERED_CODE, _("This system is currently not registered."))

        print(
            _("Unregistering from: {hostname}:{port}{prefix}").format(
                hostname=conf["server"]["hostname"],
                port=conf["server"]["port"],
                prefix=conf["server"]["prefix"],
            )
        )
        try:
            unregister.UnregisterService(self.cp).unregister()
        except Exception as e:
            handle_exception("Unregister failed", e)

        # managerlib.unregister reloads the now None provided identity
        # so cp_provider provided auth_cp's should fail, like the below

        # This block is simply to ensure that the yum repos got updated. If it fails,
        # there is no issue since it will most likely be cleaned up elsewhere (most
        # likely by the yum plugin)
        try:
            # there is no consumer cert at this point, a uep object
            # is not useful
            cleanup_certmgr = UnregisterActionClient()
            cleanup_certmgr.update()
        except Exception:
            pass

        self._request_validity_check()

        # We have new credentials, restart virt-who
        restart_virt_who()

        print(_("System has been unregistered."))
