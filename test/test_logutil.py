import logging

import mock

import fixture

from subscription_manager import logutil


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

    def test_file_config(self):
        logutil.file_config(logging_config="test/test-logging.conf")
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm")
        self.assertEqual(sm_logger.getEffectiveLevel(), logging.DEBUG)
        self.assertEqual(rhsm_logger.getEffectiveLevel(), logging.DEBUG)

    @mock.patch.object(logutil, 'LOGGING_CONFIG', "test/test-logging.conf")
    def test_log_init(self):
        logutil.init_logger()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertEqual(sm_logger.getEffectiveLevel(), logging.DEBUG)
        self.assertEqual(rhsm_logger.getEffectiveLevel(), logging.DEBUG)

    def test_file_config_debug(self):
        with mock.patch.dict('os.environ', {'SUBMAN_DEBUG': '1'}):
            logutil.file_config(logging_config="test/test-logging.conf")
            debug_logger = logging.getLogger()
            self.assertEqual(debug_logger.getEffectiveLevel(), logging.NOTSET)

    @mock.patch.object(logutil, 'LOGGING_CONFIG', "test/test-logging.conf")
    def test_init_logger_for_yum(self):
        logutil.init_logger_for_yum()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        self.assertFalse(sm_logger.propagate)
        self.assertFalse(rhsm_logger.propagate)
