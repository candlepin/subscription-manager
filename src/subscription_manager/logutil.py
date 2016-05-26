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

LOGGING_CONFIG = "/etc/rhsm/logging.conf"
LOGFILE_PATH = "/var/log/rhsm/rhsm.log"


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


# NOTE: python 2.6 and earlier versions of the logging module
#       defined the log handlers as old style classes. In order
#       to use super(), we also inherit from 'object'
class RHSMLogHandler(logging.handlers.RotatingFileHandler, object):
    """Logging Handler for /var/log/rhsm/rhsm.log"""
    def __init__(self, *args, **kwargs):
        try:
            super(RHSMLogHandler, self).__init__(*args, **kwargs)
        # fallback to stdout if we can't open our logger
        except Exception:
            logging.StreamHandler.__init__(self)
        self.addFilter(ContextLoggingFilter(name=""))


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


def file_config(logging_config):
    """Load logging config from the file logging_config and setup logging."""

    # NOTE: without disable_existing_loggers, this would have to
    # be close to the first thing ran. Any loggers created after
    # that are disabled. This likely includes module level loggers
    # like all of ours.
    try:
        logging.config.fileConfig(logging_config,
                                  defaults={'logfilepath': LOGFILE_PATH},
                                  disable_existing_loggers=False)
    except Exception as e:
        # If the log config file doesn't exist, or is empty, we end up
        # with ConfigParser errors.

        # TODO: fallback default logger?
        print(e)


def init_logger():
    """Load logging config file and setup logging.

    Only needs to be called once per process."""

    file_config(logging_config=LOGGING_CONFIG)


def init_logger_for_yum():
    init_logger()

    # TODO: switch this to reference /etc/rhsm/yum_logging.conf

    # Don't send log records up to yum/yum plugin conduit loggers
    logging.getLogger("subscription_manager").propagate = False
    logging.getLogger("rhsm").propagate = False
    logging.getLogger("rhsm-app").propagate = False
