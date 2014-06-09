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

        # By default, we try to use a RotatingFileHandler with the rhsm log.
        # We don't want to do that for unit tests, so just return a dummy path
        mock.patch("subscription_manager.logutil._get_log_file_path", return_value="./not/a/valid/path")

        mock.patch("logging.StreamHandler", new=NullHandler)

    def tearDown(self):
        self.remove_loggers()
        super(TestLogutil, self).tearDown()
        mock.patch.stopall()

    def remove_loggers(self):
        logging.getLogger("subscription_manager").handlers = []
        logging.getLogger("rhsm").handlers = []
        logging.getLogger("rhsm-app").handlers = []
        logging.getLogger().handlers = []

    def test_init_logger(self):
        logutil.init_logger()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm")
        self.assertEqual(sm_logger.getEffectiveLevel(), logutil.LOG_LEVEL)
        self.assertEqual(rhsm_logger.getEffectiveLevel(), logutil.LOG_LEVEL)

    def test_init_logger_debug(self):
        with mock.patch.dict('os.environ', {'SUBMAN_DEBUG': '1'}):
            logutil.init_logger()
            debug_logger = logging.getLogger()
            self.assertEqual(debug_logger.getEffectiveLevel(), logging.DEBUG)

    def test_init_logger_for_yum(self):
        logutil.init_logger_for_yum()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm")
        self.assertFalse(sm_logger.propagate)
        self.assertFalse(rhsm_logger.propagate)
