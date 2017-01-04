# Copyright (c) 2016 Red Hat, Inc.
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
import dbus
import dbus.exceptions

from rhsmlib.dbus.facts.base import AllFacts
from rhsmlib.dbus.facts import constants

from test.rhsmlib_test.base import DBusObjectTest


class TestFactsDBusObject(DBusObjectTest):
    def setUp(self):
        super(TestFactsDBusObject, self).setUp()
        self.proxy = self.proxy_for(AllFacts.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.FACTS_DBUS_INTERFACE)

    def dbus_objects(self):
        return [AllFacts]

    def bus_name(self):
        return constants.FACTS_DBUS_NAME

    def test_get_facts(self):
        def assertions(*args):
            result = args[0]
            self.assertIn("uname.machine", result)

        self.dbus_request(assertions, self.interface.GetFacts)

    def test_missing_method(self):
        def assertions(*args):
            pass

        with self.assertRaises(dbus.exceptions.DBusException):
            self.dbus_request(assertions, self.interface.MissingMethod)
