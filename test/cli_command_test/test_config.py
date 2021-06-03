# -*- coding: utf-8 -*-

import sys

from rhsmlib.services import config

from ..test_managercli import TestCliCommand
from subscription_manager import managercli
from subscription_manager.cli_command import config as config_command

from ..fixture import Capture

from mock import patch


class TestConfigCommand(TestCliCommand):
    command_class = managercli.ConfigCommand

    def setUp(self):
        super(TestConfigCommand, self).setUp()
        self.original_conf = config_command.conf
        config_command.conf = config.Config(self.mock_cfg_parser)

    def tearDown(self):
        super(TestConfigCommand, self).tearDown()
        config_command.conf = self.original_conf

    def test_list(self):
        self.cc.main(["--list"])
        self.cc._validate_options()

    def test_list_default(self):
        hostname = config_command.conf['server']['hostname']
        # BZ 1862431
        config_command.conf['rhsmd'] = {}
        config_command.conf['rhsmd']['processtimeout'] = '300'
        with Capture() as cap:
            self.cc._do_command = self._orig_do_command
            self.cc.main([""])
            self.cc._validate_options()
        self.assertTrue(hostname in cap.out)

    def test_remove(self):
        self.cc.main(["--remove", "server.hostname", "--remove", "server.port"])
        self.cc._validate_options()

    def test_config_list(self):
        self.cc._do_command = self._orig_do_command
        self.cc.main(["--list"])

    def test_config(self):
        self.cc._do_command = self._orig_do_command
        # if args is empty we default to sys.argv, so stub it
        with patch.object(sys, 'argv', ['subscription-manager', 'config']):
            self.cc.main([])

    def test_set_config(self):
        self.cc._do_command = self._orig_do_command

        baseurl = 'https://someserver.example.com/foo'
        self.cc.main(['--rhsm.baseurl', baseurl])
        self.assertEqual(config_command.conf['rhsm']['baseurl'], baseurl)

    def test_remove_config_default(self):
        with Capture() as cap:
            self.cc._do_command = self._orig_do_command
            self.cc.main(['--remove', 'rhsm.baseurl'])
        self.assertTrue('The default value for' in cap.out)

    def test_remove_config_section_does_not_exist(self):
        self.cc._do_command = self._orig_do_command
        self.assertRaises(SystemExit, self.cc.main, ['--remove', 'this.doesnotexist'])

    def test_remove_config_key_does_not_exist(self):
        self.cc._do_command = self._orig_do_command
        self.assertRaises(SystemExit, self.cc.main, ['--remove', 'rhsm.thisdoesnotexist'])

    def test_remove_config_key_not_dotted(self):
        self.cc._do_command = self._orig_do_command
        self.assertRaises(SystemExit, self.cc.main, ['--remove', 'notdotted'])
