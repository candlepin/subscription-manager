from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

"""
This module holds information about current state of client application
like sender of D-bus method, current subscription-manager command (register,
attach, ...), dnf command, etc.
"""

import logging
import dbus

from rhsmlib.utils import Singleton, no_reinitialization
from rhsmlib.dbus import dbus_utils

log = logging.getLogger(__name__)


class DBusSender(Singleton):
    """
    This class holds information about current sender of D-Bus method
    """

    @no_reinitialization
    def __init__(self):
        self._cmd_line = None

    @property
    def cmd_line(self):
        with self:
            return self._cmd_line

    @cmd_line.setter
    def cmd_line(self, cmd_line):
        with self:
            self._cmd_line = cmd_line

    @staticmethod
    def get_cmd_line(sender, bus=None):
        """
        Try to get command line of sender
        :param sender: sender
        :param bus: bus
        :return:
        """
        if bus is None:
            bus = dbus.SystemBus()
        cmd_line = dbus_utils.command_of_sender(bus, sender)
        if cmd_line is not None and type(cmd_line) == str:
            # Store only first argument of command line (no argument including username or password)
            cmd_line = cmd_line.split()[0]
        return cmd_line

    def set_cmd_line(self, sender, cmd_line=None, bus=None):
        """
        This method set sender's command line in the singleton object
        :return: None
        """
        if cmd_line is None:
            self.cmd_line = self.get_cmd_line(sender, bus)
        else:
            self.cmd_line = cmd_line
        log.debug("D-Bus sender: %s (cmd-line: %s)" % (sender, self.cmd_line))

    def reset_cmd_line(self):
        """
        Reset sender's command line
        :return: None
        """
        self.cmd_line = None
