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

from rhsmlib.dbus.objects.consumer import ConsumerDBusImplementation

from unittest import mock
from test.rhsmlib.base import SubManDBusFixture


class TestConsumerDBusObject(SubManDBusFixture):
    @classmethod
    def setUpClass(cls) -> None:
        get_consumer_uuid_patch = mock.patch(
            "rhsmlib.dbus.objects.consumer.Consumer.get_consumer_uuid",
            name="get_consumer_uuid",
        )
        cls.patches["get_consumer_uuid"] = get_consumer_uuid_patch.start()
        cls.addClassCleanup(get_consumer_uuid_patch)

        cls.impl = ConsumerDBusImplementation()

        super().setUpClass()

    def test_GetUuid(self):
        self.patches["get_consumer_uuid"].return_value = "fake-uuid"

        expected = "fake-uuid"
        result = self.impl.get_uuid()
        self.assertEqual(expected, result)
