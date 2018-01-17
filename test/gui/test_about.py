from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.gui import about
from test.fixture import OPEN_FUNCTION
from nose.plugins.attrib import attr


@attr('gui')
class TestAboutDialog(unittest.TestCase):
    @mock.patch('subscription_manager.gui.about.get_server_versions')
    @mock.patch('subscription_manager.gui.about.get_client_versions')
    @mock.patch(OPEN_FUNCTION)
    def test(self, open_mock, client_versions_mock, server_versions_mock):
        backend_mock = mock.Mock()
        open_mock.return_value = '1367419386'

        server_versions_mock.return_value = {"candlepin": '100-1.0',
                                             "server-type": 'candlepin'}
        client_versions_mock.return_value = {"subscription-manager": "5.1.3-45fsfrsdf",
                                             "python-rhsm": "234234234-1.0rc6"}

        about_dialog = about.AboutDialog(None, backend_mock)
        about_dialog.show()
        # a response we do not how to handle
        about_dialog.dialog.emit("response",
                                 ga_Gtk.ResponseType.YES)
        # and a "response" we know how to handle
        about_dialog.dialog.emit("response",
                                 ga_Gtk.ResponseType.CANCEL)
