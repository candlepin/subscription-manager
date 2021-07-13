from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2005-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import logging
import logging.handlers
import logging.config
import os
import sys
import rhsm.config

LOGFILE_DIR = "/var/log/rhsm/"

LOGFILE_PATH = os.path.join(LOGFILE_DIR, "rhsm.log")

LOG_FORMAT = u'%(asctime)s [%(levelname)s] %(cmd_name)s:%(process)d:' \
             u'%(threadName)s @%(filename)s:%(lineno)d - %(message)s'

_rhsm_log_handler = None
_subman_debug_handler = None
log = None
ROOT_NAMESPACES = ['subscription_manager',
                   'rhsm',
                   'rhsm-app',
                   'rhsmlib',
                   'syspurpose',
                   'cloud_what'
                   ]


# Don't need this for syslog
class ContextLoggingFilter(object):
    """Find the name of the process as 'cmd_name'"""
    current_cmd = os.path.basename(sys.argv[0])
    cmd_line = ' '.join(sys.argv)

    def __init__(self, name):
        self.name = name

    def filter(self, record):
        record.cmd_name = self.current_cmd
        record.cmd_line = self.cmd_line

        # TODO: if we merge "no-rpm-version" we could populate it here
        return True


class SubmanDebugLoggingFilter(object):
    """Filter all log records unless env SUBMAN_DEBUG exists

    Used to turn on stdout logging for cli debugging."""

    def __init__(self, name):
        self.name = name
        self.on = 'SUBMAN_DEBUG' in os.environ

    def filter(self, record):
        return self.on


def RHSMLogHandler(*args, **kwargs):
    """Factory for Logging Handler for /var/log/rhsm/rhsm.log"""
    err = None
    try:
        result = logging.handlers.RotatingFileHandler(*args, **kwargs)
    except Exception as error:
        result = logging.StreamHandler()
        # Try to create log directory and try to set handle once again
        if not os.path.exists(LOGFILE_DIR):
            try:
                os.makedirs(LOGFILE_DIR)
                result = logging.handlers.RotatingFileHandler(*args, **kwargs)
            except Exception as error:
                err = "{error} - Further logging output will be written to stderr".format(error=error)
        else:
            err = "{error} - Further logging output will be written to stderr".format(error=error)
    result.addFilter(ContextLoggingFilter(name=""))
    return result, err


class SubmanDebugHandler(logging.StreamHandler, object):
    """Logging Handler for cli debugging.

    This handler only emits records if SUBMAN_DEBUG exists in os.environ."""

    def __init__(self, *args, **kwargs):
        super(SubmanDebugHandler, self).__init__(*args, **kwargs)
        self.addFilter(ContextLoggingFilter(name=""))
        self.addFilter(SubmanDebugLoggingFilter(name=""))


# Note: this only does anything for python 2.6+, if the
# logging module has 'captureWarnings'. Otherwise it will not
# be triggered.
class PyWarningsLoggingFilter(object):
    """Add a prefix to the messages from py.warnings.

    To help distinquish log messages from python and pygtk 'warnings',
    while avoiding changing the log format."""

    label = "py.warnings:"

    def __init__(self, name):
        self.name = name

    def filter(self, record):
        record.msg = u'%s %s' % (self.label, record.msg)
        return True


class PyWarningsLogger(logging.getLoggerClass()):
    """Logger for py.warnings for use in file based logging config."""
    level = logging.WARNING

    def __init__(self, name):
        super(PyWarningsLogger, self).__init__(name)

        self.setLevel(self.level)
        self.addFilter(PyWarningsLoggingFilter(name="py.warnings"))


def _get_default_rhsm_log_handler():
    global _rhsm_log_handler
    error = None
    if not _rhsm_log_handler:
        _rhsm_log_handler, error = RHSMLogHandler(LOGFILE_PATH)
        _rhsm_log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return _rhsm_log_handler, error


def _get_default_subman_debug_handler():
    global _subman_debug_handler
    if not _subman_debug_handler:
        _subman_debug_handler = SubmanDebugHandler()
        _subman_debug_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return _subman_debug_handler


def init_logger(config=None):
    """Load logging config file and setup logging.

    Only needs to be called once per process."""

    global log
    if log:
        log.warning("logging already initialized")

    if config is None:
        config = rhsm.config.get_config_parser()

    # This is little bit hackish, because it will probably work only for subscription-manager,
    # because only subscription-manager can set default_log_level using CLI option. If any
    # other CLI will want to set default_log_level, then it has to use same CLI option as
    # subscription-manager does (--logging.default_log_level)
    default_log_level = None
    for arg in sys.argv:
        if arg.startswith('--logging.default_log_level'):
            # It is possible to use --logging.default_log_level=VALUE and
            # --logging.default_log_level VALUE
            option_value = arg.split()
            if len(option_value) == 1:
                option_value = arg.split('=')

            if len(option_value) == 2:
                default_log_level = option_value[1]
                # When not valid value is provided, then set default_log_level to None
                # Warning message will be printed later, when not valid value will be
                # saved to config file
                if config.is_log_level_valid(default_log_level, print_warning=False) is False:
                    default_log_level = None

    if default_log_level is None:
        default_log_level = config.get('logging', 'default_log_level')
        if not config.is_log_level_valid(default_log_level):
            # This is not a valid logging level, set to INFO
            default_log_level = 'INFO'

    pending_error_messages = []

    for root_namespace in ROOT_NAMESPACES:
        logger = logging.getLogger(root_namespace)
        rhsm_handler, error = _get_default_rhsm_log_handler()
        if error:
            pending_error_messages.append(error)
        logger.addHandler(rhsm_handler)
        logger.addHandler(_get_default_subman_debug_handler())
        logger.setLevel(getattr(logging, default_log_level.strip()))

    for logger_name, logging_level in config.items('logging'):
        logger_name = logger_name.strip()
        if logger_name.split('.')[0] not in ROOT_NAMESPACES:
            # Don't allow our logging configuration to mess with loggers
            # outside the namespaces we claim as ours
            # Also ignore other more general configuration options like
            # default_log_level
            continue
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, logging_level.strip()))

    if not log:
        log = logging.getLogger(__name__)

    # RHBZ#1782910 Previously to handle the case of not being able to create
    # the /var/log/rhsm/rhsm.log file to log to, we were logging an error level message
    # by doing `logging.error("Our error message here"). Doing that at a point where
    # there is nothing configured for the root logger causes a StreamHandler to be added to
    # the root logger. That then caused all dnf python logging to be written to stderr.
    # To be able to output the log messages which happen during set up, we queue the errors
    # and log them using our resulting logger which has been setup (after adding our own
    # StreamHandler but not to the root logger).
    for error_message in pending_error_messages:
        log.error(error_message)


def init_logger_for_yum():
    init_logger()

    # Don't send log records up to yum/yum plugin conduit loggers
    for logger_name in ROOT_NAMESPACES:
        logging.getLogger(logger_name).propagate = False
