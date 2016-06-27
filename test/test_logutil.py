import logging
import os
import copy

import mock

import fixture

from subscription_manager import logutil

TEST_LOG_CONFIG = os.path.join(os.path.dirname(__file__), "test-logging.conf")
TEST_PLUGIN_LOG_CONFIG = os.path.join(os.path.dirname(__file__), "test-plugin-log-config.conf")
TEST_LOGGING_CONFIG = """{
  "version": 1,
  "disable_existing_loggers": false,
  "root": {
    "level": "DEBUG",
    "handlers": [
      "subman_debug"
    ]
  },
  "loggers": {
    "rhsm-app": {
      "level": "DEBUG",
      "handlers": [
        "rhsmlog"
      ]
    },
    "rhsm": {
      "level": "DEBUG",
      "handlers": [
        "rhsmlog"
      ]
    },
    "subscription_manager": {
      "level": "DEBUG",
      "handlers": [
        "rhsmlog"
      ]
    },
    "py.warnings": {
      "level": "WARNING",
      "handlers": [
        "rhsmlog"
      ]
    }
  },
  "formatters": {
    "syslog": {
      "format": "[%(levelname)s] @%(filename)s:%(lineno)d - %(message)s"
    },
    "rhsmlog": {
      "format": "%(asctime)s [%(levelname)s] %(cmd_name)s:%(process)d @%(filename)s:%(lineno)d - %(message)s"
    },
    "subman_debug": {
      "format": "%(asctime)s [%(name)s %(levelname)s] %(cmd_name)s(%(process)d):%(threadName)s @%(filename)s:%(funcName)s:%(lineno)d - %(message)s"
    }
  },
  "handlers": {
    "syslog": {
      "level": "INFO",
      "formatter": "syslog",
      "class": "logging.handlers.SysLogHandler",
      "address": "/dev/log"
    },
    "rhsmlog": {
      "level": "INFO",
      "formatter": "rhsmlog",
      "class": "subscription_manager.logutil.RHSMLogHandler",
      "filename": "%(logfilepath)s"
    },
    "subman_debug": {
      "level": "DEBUG",
      "formatter": "subman_debug",
      "class": "subscription_manager.logutil.SubmanDebugHandler"
    }
  }
}
"""


# no NullHandler in 2.6, include our own
class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class TestLogutil(fixture.SubManFixture):
    def setUp(self):
        super(TestLogutil, self).setUp()

    def tearDown(self):
        self.remove_loggers()
        super(TestLogutil, self).tearDown()
        mock.patch.stopall()

    def remove_loggers(self):
        logging.getLogger("subscription_manager").handlers = []
        logging.getLogger("rhsm").handlers = []
        logging.getLogger("rhsm-app").handlers = []
        logging.getLogger().handlers = []

    def test_apply_defaults(self):
        defaults = {'test': 'test', 'test_two': 'test_two'}
        test_dict = {
            'random_key': '%(test)s',
            'random_key_two': {
                'random_key_three': '%(test_two)s'
            }
        }
        expected = {
            'random_key': '%(test)s' % defaults,
            'random_key_two': {
                'random_key_three': '%(test_two)s' % defaults
            }
        }
        result = logutil.apply_defaults(test_dict, defaults)
        self.assertDictEqual(result, expected)

    @mock.patch('subscription_manager.logutil.apply_defaults')
    @mock.patch('subscription_manager.logutil.dict_config')
    def test_init_logger(self, mock_dict_config, mock_apply_defaults):
        expected = "Expected"
        mock_apply_defaults.return_value = "Expected"
        logutil.init_logger(path_to_config=TEST_LOG_CONFIG)
        mock_dict_config.assert_called_with(expected)

    @mock.patch('__builtin__.file')
    @mock.patch.object(logutil, 'LOGGING_CONFIG', TEST_LOG_CONFIG)
    def test_log_init(self, file_mock):
        file_mock.return_value.read.return_value = TEST_LOGGING_CONFIG
        logutil.init_logger()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertEqual(sm_logger.getEffectiveLevel(), logging.DEBUG)
        self.assertEqual(rhsm_logger.getEffectiveLevel(), logging.DEBUG)

    def _setup_root_logger(self):
        root = logging.getLogger()
        null_handler = NullHandler()
        root.addHandler(null_handler)
        return root

    @mock.patch.object(logutil, 'PLUGIN_LOGGING_CONFIG', TEST_PLUGIN_LOG_CONFIG)
    def test_init_logger_for_yum(self):
        root = self._setup_root_logger()
        handlers_before = copy.copy(root.handlers)
        logutil.init_logger_for_yum()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertFalse(sm_logger.propagate)
        self.assertFalse(rhsm_logger.propagate)
        self.assertListEqual(handlers_before, root.handlers)
