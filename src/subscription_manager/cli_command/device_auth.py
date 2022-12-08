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
import getpass
import readline
import os

from subscription_manager.cli_command.cli import CliCommand
from subscription_manager.cli import system_exit
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import is_interactive


class DeviceAuthCommand(CliCommand):
    """
    Abstract class for commands that require a username and password
    """

    def __init__(self, name, shortdesc=None, primary=False):
        super(DeviceAuthCommand, self).__init__(name, shortdesc, primary)
        self._device_auth = None

    def _get_oauth(self):
        """
        Safely get a username and password from the tty, without echoing.
        if either username or password are provided as arguments, they will
        not be prompted for. In a non-interactive session, the system exits with an error.
        """
        # Jason PoC for device auth workflow
        candlepin_status = self.cp.getStatus()
        print(candlepin_status)
        can_do_device_auth = "device_auth" in candlepin_status["managerCapabilities"]
        print(_("Device auth supported: {}".format(can_do_device_auth)))
        auth_host = candlepin_status["deviceAuthUrl"]
        client_id = "subscription-manager"  # candlepin_status["deviceAuthClientId"]
        scope = candlepin_status["deviceAuthScope"]
        if can_do_device_auth:
            print("Auth Host: {auth_host}, Client Id: {client_id}, Scope: {scope}".format(auth_host=auth_host, client_id=client_id, scope=scope))
            handler = "/auth"
            self.cp_provider.set_connection_info(
                host="sso.stage.redhat.com",
                ssl_port="443",
                handler=handler
            )
            oauth_conn = self.cp_provider.get_oauth_cp()
            print(oauth_conn)
            print(oauth_conn.handler)
            oauth_resp = oauth_conn.postDeviceAuth(client_id, scope)
            print(oauth_resp)

        return True

