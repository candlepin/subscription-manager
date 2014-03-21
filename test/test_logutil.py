import logging
import os

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
        mock.patch("subscription_manager.logutil._get_log_file_path", return_value="./not/a/valid/path")
        mock.patch("logging.StreamHandler", new=NullHandler)

    def tearDown(self):
        super(TestLogutil, self).tearDown()
        mock.patch.stopall()
        self.remove_loggers()

    def remove_loggers(self):
        logging.getLogger("subscription_manager").handlers = []
        logging.getLogger("rhsm").handlers = []
        logging.getLogger("rhsm-app").handlers = []

    def test_init_logger(self):
        logutil.init_logger()

    def test_init_logger_debug(self):
        os.environ['SUBMAN_DEBUG'] = "1"
        logutil.init_logger()

    def test_init_logger_for_yum(self):
        logutil.init_logger_for_yum()
