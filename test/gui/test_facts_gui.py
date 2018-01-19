from __future__ import print_function, division, absolute_import

from test.fixture import SubManFixture

from subscription_manager.injection import provide, IDENTITY
from test.stubs import StubUEP, StubFacts
from subscription_manager.gui import factsgui
from mock import NonCallableMock, patch
from nose.plugins.attrib import attr


@attr('gui')
class FactDialogTests(SubManFixture):

    def setUp(self):

        super(FactDialogTests, self).setUp()

        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': 'Unknown',
                          'system.uuid': 'MOCKUUID'}

        self.expected_facts = expected_facts
        self.stub_facts = StubFacts(expected_facts)

    def test_hides_environment_when_not_supported(self):
        dialog = factsgui.SystemFactsDialog()
        dialog.display_facts()
        self.assertEqual(False, dialog.environment_title.get_property("visible"))
        self.assertEqual(False, dialog.environment_label.get_property("visible"))

    def test_shows_unknown_for_no_org(self):
        dialog = factsgui.SystemFactsDialog()
        dialog.display_facts()
        #No owner id should show if we have no owner
        self.assertEqual(False, dialog.owner_label.get_property("visible"))
        self.assertEqual(False, dialog.owner_title.get_property("visible"))

    @patch.object(StubUEP, 'getOwner')
    def test_shows_org_id(self, mock_getOwner):
        mock_getOwner.return_value = {'displayName': 'foo', 'key': 'bar'}
        dialog = factsgui.SystemFactsDialog()
        dialog.display_facts()
        self.assertEqual(True, dialog.owner_label.get_property("visible"))
        self.assertEqual(True, dialog.owner_title.get_property("visible"))
        self.assertEqual('foo (bar)', dialog.owner_label.get_label())

    @patch.object(StubUEP, 'supports_resource')
    @patch.object(StubUEP, 'getConsumer')
    def test_shows_environment_when_supported(self, mock_getConsumer, mock_supports_resource):
        mock_supports_resource.return_value = True
        mock_getConsumer.return_value = {'environment': {'name': 'foobar'}}
        dialog = factsgui.SystemFactsDialog()
        dialog.display_facts()
        self.assertEqual(True, dialog.environment_title.get_property("visible"))
        self.assertEqual(True, dialog.environment_label.get_property("visible"))
        self.assertEqual("foobar", dialog.environment_label.get_text())

    @patch.object(StubUEP, 'supports_resource')
    @patch.object(StubUEP, 'getConsumer')
    def test_shows_environment_when_empty(self, mock_getConsumer, mock_supports_resource):
        mock_supports_resource.return_value = True
        mock_getConsumer.return_value = {'environment': None}
        dialog = factsgui.SystemFactsDialog()
        dialog.display_facts()
        self.assertEqual(True, dialog.environment_title.get_property("visible"))
        self.assertEqual(True, dialog.environment_label.get_property("visible"))
        self.assertEqual("None", dialog.environment_label.get_text())

    def test_update_button_disabled(self):
        # Need an unregistered consumer object:
        id_mock = NonCallableMock()
        id_mock.name = None
        id_mock.uuid = None

        def new_identity():
            return id_mock
        provide(IDENTITY, new_identity)

        dialog = factsgui.SystemFactsDialog()
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertFalse(enabled)

    def test_update_button_enabled(self):
        dialog = factsgui.SystemFactsDialog()
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertTrue(enabled)
