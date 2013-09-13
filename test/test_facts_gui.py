import sys
from fixture import SubManFixture

import rhsm_display
rhsm_display.set_display()

from subscription_manager.injection import provide, IDENTITY
from stubs import MockStderr, MockStdout, StubUEP, StubBackend, StubFacts
from subscription_manager.gui import factsgui
from mock import Mock, patch


class FactDialogTests(SubManFixture):

    def setUp(self):

        super(FactDialogTests, self).setUp()

        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': 'Unknown',
                          'system.uuid': 'MOCKUUID'}

        self.expected_facts = expected_facts
        self.stub_facts = StubFacts(expected_facts)

        self.backend = StubBackend()

        id_mock = Mock()
        id_mock.name = 'system'
        id_mock.uuid = 'Random UUID'
        id_mock.exists_and_valid = Mock(return_value=True)
        provide(IDENTITY, id_mock)

        sys.stderr = MockStderr
        sys.stdout = MockStdout

    def tearDown(self):
        sys.stderr = sys.__stderr__
        sys.stdout = sys.__stdout__

    def test_facts_are_displayed(self):
        found_facts = {}

        def check_facts(parent, facts):
            found_facts[facts[0]] = facts[1]

        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.facts_store.append = check_facts
        dialog.display_facts()

        self.assertEquals(self.expected_facts, found_facts)

    def test_hides_environment_when_not_supported(self):
        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.display_facts()
        self.assertEquals(False, dialog.environment_hbox.get_property("visible"))

    def test_shows_unknown_for_no_org(self):
        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.display_facts()
        #No owner id should show if we have no owner
        self.assertEquals(False, dialog.owner_id_hbox.get_property("visible"))
        self.assertEquals('Unknown', dialog.owner_label.get_label())

    @patch.object(StubUEP, 'getOwner')
    def test_shows_org_id(self, mock_getOwner):
        mock_getOwner.return_value = {'displayName': 'foo', 'key': 'bar'}
        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.display_facts()
        self.assertEquals(True, dialog.owner_id_hbox.get_property("visible"))
        self.assertEquals('bar', dialog.owner_id_label.get_label())

    @patch.object(StubUEP, 'supports_resource')
    @patch.object(StubUEP, 'getConsumer')
    def test_shows_environment_when_supported(self, mock_getConsumer, mock_supports_resource):
        mock_supports_resource.return_value = True
        mock_getConsumer.return_value = {'environment': {'name': 'foobar'}}
        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.display_facts()
        self.assertEquals(True, dialog.environment_hbox.get_property("visible"))
        self.assertEquals("foobar", dialog.environment_label.get_text())

    @patch.object(StubUEP, 'supports_resource')
    @patch.object(StubUEP, 'getConsumer')
    def test_shows_environment_when_empty(self, mock_getConsumer, mock_supports_resource):
        mock_supports_resource.return_value = True
        mock_getConsumer.return_value = {'environment': None}
        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.display_facts()
        self.assertEquals(True, dialog.environment_hbox.get_property("visible"))
        self.assertEquals("None", dialog.environment_label.get_text())

    def test_update_button_disabled(self):
        # Need an unregistered consumer object:
        id_mock = Mock()
        id_mock.name = None
        id_mock.uuid = None

        def new_identity():
            return id_mock
        provide(IDENTITY, new_identity)

        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertFalse(enabled)

    def test_update_button_enabled(self):

        id_mock = Mock()
        id_mock.getConsumerName.return_value = 'system'
        id_mock.getConsumerId.return_value = 'Random UUID'
        provide(IDENTITY, id_mock)

        dialog = factsgui.SystemFactsDialog(self.backend,
                                            self.stub_facts)
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertTrue(enabled)
