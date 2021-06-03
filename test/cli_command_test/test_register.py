# -*- coding: utf-8 -*-

import sys

from ..test_managercli import TestCliProxyCommand
from subscription_manager import syspurposelib
from subscription_manager import managercli

from mock import patch


class TestRegisterCommand(TestCliProxyCommand):
    command_class = managercli.RegisterCommand

    def setUp(self):
        super(TestRegisterCommand, self).setUp()
        self._inject_mock_invalid_consumer()
        argv_patcher = patch.object(sys, 'argv', ['subscription-manager', 'register'])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)
        syspurposelib.USER_SYSPURPOSE = self.write_tempfile("{}").name

    def tearDown(self):
        super(TestRegisterCommand, self).tearDown()
        syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

    def test_keys_and_consumerid(self):
        self._test_exception(["--consumerid", "22", "--activationkey", "key"])

    def test_force_and_consumerid(self):
        self._test_exception(["--consumerid", "22", "--force"])

    def test_key_and_org(self):
        self._test_no_exception(["--activationkey", "key", "--org", "org"])

    def test_key_and_no_org(self):
        self._test_exception(["--activationkey", "key"])

    def test_empty_string_key_and_org(self):
        self._test_exception(["--activationkey=", "--org", "org"])

    def test_keys_and_username(self):
        self._test_exception(["--username", "bob", "--activationkey", "key"])

    def test_keys_and_environments(self):
        self._test_exception(["--environment", "JarJar", "--activationkey", "Binks"])

    def test_env_and_org(self):
        self._test_no_exception(["--env", "env", "--org", "org"])

    def test_no_commands(self):
        self._test_no_exception([])

    def test_main_server_url(self):
        with patch.object(self.mock_cfg_parser, "save") as mock_save:
            server_url = "https://subscription.rhsm.redhat.com/subscription"
            self._test_no_exception(["--serverurl", server_url])
            mock_save.assert_called_with()

    def test_main_base_url(self):
        with patch.object(self.mock_cfg_parser, "save") as mock_save:
            base_url = "https://cdn.redhat.com"
            self._test_no_exception(["--baseurl", base_url])
            mock_save.assert_called_with()

    def test_insecure(self):
        with patch.object(self.mock_cfg_parser, "save") as mock_save:
            self._test_no_exception(["--insecure"])
            mock_save.assert_called_with()

    def test_token(self):
        self._test_no_exception(["--token", "eyJhbGciOiJSUzI1NiIsInR5cCIg"])
