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
from logging.handlers import RotatingFileHandler
import os
import sys

RHSM_LOG = '/var/log/rhsm/rhsm.log'
CERT_LOG = '/var/log/rhsm/rhsmcertd.log'

handler = None
stdout_handler = None

LOG_FORMAT = u'%(asctime)s [%(levelname)s] %(cmd_name)s ' \
              '@%(filename)s:%(lineno)d - %(message)s'

LOG_LEVEL = logging.DEBUG

DEBUG_LOG_FORMAT = u'%(asctime)s [%(name)s %(levelname)s] ' \
                    '%(cmd_name)s(%(process)d):%(threadName)s ' \
                    '@%(filename)s:%(funcName)s:%(lineno)d - %(message)s'


def _get_log_file_path():
    path = RHSM_LOG
    try:
        if not os.path.isdir("/var/log/rhsm"):
            os.mkdir("/var/log/rhsm")
    except EnvironmentError:
        # ignore failures to create log dir
        # /var/log may be read-only in rhel5 anaconda and
        # we don't want to break anaconda
        # see https://bugzilla.redhat.com/show_bug.cgi?id=670973#c54
        pass
    return path


def _get_handler():
    # we only need one global handler
    global handler
    if handler is not None:
        return handler

    path = _get_log_file_path()

    # Try to write to /var/log, fallback on console logging:
    try:
        handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5, encoding='utf-8')
    except IOError:
        handler = logging.StreamHandler()
    except Exception:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(LOG_LEVEL)
    handler.addFilter(ContextLoggingFilter(name=""))

    return handler


def _get_stdout_handler():
    global stdout_handler
    if stdout_handler is not None:
        return stdout_handler

    handler = logging.StreamHandler()
    handler.addFilter(ContextLoggingFilter(name=""))

    return handler


class ContextLoggingFilter(object):
    current_cmd = os.path.basename(sys.argv[0])
    cmd_line = ' '.join(sys.argv)

    def __init__(self, name):
        self.name = name

    def filter(self, record):
        record.cmd_name = self.current_cmd
        record.cmd_line = self.cmd_line

        # TODO: if we merge "no-rpm-version" we could populate it here
        return True


def init_logger():

    handler = _get_handler()

    logging.getLogger("subscription_manager").setLevel(LOG_LEVEL)
    logging.getLogger("rhsm").setLevel(LOG_LEVEL)
    # FIXME: remove 'rhsm-app' when we rename all the loggers
    logging.getLogger("rhsm-app").setLevel(LOG_LEVEL)

    logging.getLogger("subscription_manager").addHandler(_get_handler())
    logging.getLogger("rhsm").addHandler(_get_handler())
    # FIXME: remove
    logging.getLogger("rhsm-app").addHandler(_get_handler())

    # dump logs to stdout, and (re)set log level
    # to DEBUG
    if 'SUBMAN_DEBUG' in os.environ:
        handler = _get_stdout_handler()

        handler.setFormatter(logging.Formatter(DEBUG_LOG_FORMAT))
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)


def init_logger_for_yum():
    init_logger()

    # Don't send log records up to yum/yum plugin conduit loggers
    logging.getLogger("subscription_manager").propagate = False
    logging.getLogger("rhsm").propagate = False
    logging.getLogger("rhsm-app").propagate = False
