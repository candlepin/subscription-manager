import logging

import mock

import fixture

import stubs

from subscription_manager import logutil


# no NullHandler in 2.6, include our own
class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class TestLogutil(fixture.SubManFixture):
    def setUp(self):
        super(TestLogutil, self).setUp()
        self.rhsm_config = stubs.StubConfig()
        rhsm_patcher = mock.patch('rhsm.config')
        self.rhsm_config_mock = rhsm_patcher.start()
        self.rhsm_config_mock.initConfig.return_value = self.rhsm_config
        self.addCleanup(rhsm_patcher.stop)

    def tearDown(self):
        self.remove_loggers()
        super(TestLogutil, self).tearDown()

    def remove_loggers(self):
        logging.getLogger("subscription_manager").handlers = []
        logging.getLogger("rhsm").handlers = []
        logging.getLogger("rhsm-app").handlers = []
        logging.getLogger().handlers = []

    def test_log_init(self):
        logutil.init_logger()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertEqual(sm_logger.getEffectiveLevel(), logging.DEBUG)
        self.assertEqual(rhsm_logger.getEffectiveLevel(), logging.DEBUG)

    def test_log_init_default_log_level(self):
        self.rhsm_config.set("logging", "default_log_level", "WARNING")

        logutil.init_logger()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertEqual(sm_logger.getEffectiveLevel(), logging.WARNING)
        self.assertEqual(rhsm_logger.getEffectiveLevel(), logging.WARNING)

    def test_init_logger_for_yum(self):
        logutil.init_logger_for_yum()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertFalse(sm_logger.propagate)
        self.assertFalse(rhsm_logger.propagate)

    def test_do_not_modify_root_logger(self):
        root_handlers = logging.getLogger().handlers
        logutil.init_logger()
        self.assert_items_equals(logging.getLogger().handlers, root_handlers)

    def test_set_valid_logger_level(self):
        logging_conf = [
            ('subscription_manager.managercli', logging.ERROR),
            ('rhsm', logging.WARNING),
            ('rhsm-app', logging.CRITICAL),
            ('rhsm-app.rhsmd', "DEBUG")
        ]

        for logger_name, log_level in logging_conf:
            self.rhsm_config.set('logging', logger_name, log_level)

        logutil.init_logger()

        for logger_name, log_level in logging_conf:
            real_log_level = logging.getLogger(logger_name).getEffectiveLevel()
            self.assertEqual(real_log_level, logging._checkLevel(log_level))

    def test_set_invalid_logger_level(self):
        test_logger_name = 'foobar'
        initial_level = logging.ERROR
        test_logger = logging.getLogger(test_logger_name)
        test_logger.setLevel(initial_level)
        config_level = logging.DEBUG
        self.rhsm_config.set('logging', test_logger_name,
                             config_level)

        logutil.init_logger()

        self.assertNotEqual(test_logger.getEffectiveLevel(), config_level)
