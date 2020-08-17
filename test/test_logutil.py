from __future__ import print_function, division, absolute_import

import logging

import mock
import tempfile
import os

from . import fixture

from . import stubs

from rhsm import logutil


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
        self.rhsm_config_mock.get_config_parser.return_value = self.rhsm_config
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
        sm_effective = sm_logger.getEffectiveLevel()
        rhsm_effective = rhsm_logger.getEffectiveLevel()
        # Fun hack for 2.6/2.7 interoperability
        self.assertTrue(
            logging.DEBUG == sm_effective or
            logging._levelNames[sm_effective] == logging.DEBUG)
        self.assertTrue(
            logging.DEBUG == rhsm_effective or
            logging._levelNames[rhsm_effective] == logging.DEBUG)

    def test_log_init_default_log_level(self):
        self.rhsm_config.set("logging", "default_log_level", "WARNING")

        logutil.init_logger()
        sm_logger = logging.getLogger("subscription_manager")
        rhsm_logger = logging.getLogger("rhsm-app")
        sm_effective = sm_logger.getEffectiveLevel()
        rhsm_effective = rhsm_logger.getEffectiveLevel()
        # Fun hack for 2.6/2.7 interoperability
        self.assertTrue(
            logging.WARNING == sm_effective or
            logging._levelNames[sm_effective] == logging.WARNING)
        self.assertTrue(
            logging.WARNING == rhsm_effective or
            logging._levelNames[rhsm_effective] == logging.WARNING)

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
            ('subscription_manager.managercli', "ERROR"),
            ('rhsm', "WARNING"),
            ('rhsm-app', "CRITICAL")
        ]

        for logger_name, log_level in logging_conf:
            self.rhsm_config.set('logging', logger_name, log_level)

        logutil.init_logger()

        for logger_name, log_level in logging_conf:
            real_log_level = logging.getLogger(logger_name).getEffectiveLevel()
            self.assertTrue(
                logging.getLevelName(log_level) == real_log_level or
                log_level == real_log_level)

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

    def test_missing_log_directory(self):
        """
        Test creating directory for log directory
        """
        temp_dir_path = tempfile.mkdtemp()

        old_dir_path = logutil.LOGFILE_DIR
        old_file_path = logutil.LOGFILE_PATH

        # Set logutil to uninitialized state
        logutil._rhsm_log_handler = None
        logutil._subman_debug_handler = None
        logutil.LOGFILE_DIR = temp_dir_path
        logutil.LOGFILE_PATH = os.path.join(temp_dir_path, "rhsm.log")

        self.assertTrue(os.path.exists(temp_dir_path))

        # Simulate deleting of directory /var/log/rhsm
        os.rmdir(temp_dir_path)

        logutil.init_logger()

        # init_logger should automatically create directory /var/log/rhsm,
        # when it doesn't exist
        self.assertTrue(os.path.exists(temp_dir_path))

        os.remove(logutil.LOGFILE_PATH)
        os.rmdir(logutil.LOGFILE_DIR)

        logutil.LOGFILE_DIR = old_dir_path
        logutil.LOGFILE_PATH = old_file_path

    def test_not_possible_to_create_log_dir_due_to_access_perm(self):
        """
        Test that it is not possible to create log directory due to access permission
        """
        temp_dir_path = tempfile.mkdtemp()
        os.chmod(temp_dir_path, 444)

        old_dir_path = logutil.LOGFILE_DIR
        old_file_path = logutil.LOGFILE_PATH

        # Set logutil to uninitialized state
        logutil._rhsm_log_handler = None
        logutil._subman_debug_handler = None
        logutil.LOGFILE_DIR = os.path.join(temp_dir_path, "rhsm")
        logutil.LOGFILE_PATH = os.path.join(logutil.LOGFILE_DIR, "rhsm.log")

        self.assertTrue(os.path.exists(temp_dir_path))

        with fixture.Capture() as cap:
            logutil.init_logger()

        self.assertTrue("Further logging output will be written to stderr" in cap.err)

        # init_logger should not be able to automatically create directory /var/log/rhsm,
        # when user does not have access permission for that
        self.assertFalse(os.path.exists(logutil.LOGFILE_DIR))

        os.chmod(temp_dir_path, 744)
        os.rmdir(temp_dir_path)

        logutil.LOGFILE_DIR = old_dir_path
        logutil.LOGFILE_PATH = old_file_path

    def test_wrong_rhsm_log_priv(self):
        """
        Test that error messages are not printed to stderr, when it is not possible
        to print error messages to rhsm.log during initialization of logger
        """
        # Create temporary log directory
        temp_dir_path = tempfile.mkdtemp()
        # Create temporary log file
        temp_log_file = os.path.join(temp_dir_path, "rhsm.log")
        with open(temp_log_file, "w") as fp:
            fp.write("")
        # Change permission to directory /var/log/rhsm and log file
        os.chmod(temp_log_file, 444)
        os.chmod(temp_dir_path, 444)

        old_dir_path = logutil.LOGFILE_DIR
        old_file_path = logutil.LOGFILE_PATH

        # Set logutil to uninitialized state
        logutil._rhsm_log_handler = None
        logutil._subman_debug_handler = None
        logutil.LOGFILE_DIR = temp_dir_path
        logutil.LOGFILE_PATH = os.path.join(temp_log_file)

        with fixture.Capture() as cap:
            logutil.init_logger()

        self.assertTrue("Further logging output will be written to stderr" in cap.err)

        os.chmod(temp_dir_path, 744)
        os.chmod(temp_log_file, 744)
        os.remove(logutil.LOGFILE_PATH)
        os.rmdir(logutil.LOGFILE_DIR)

        logutil.LOGFILE_DIR = old_dir_path
        logutil.LOGFILE_PATH = old_file_path
