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

CERT_LOG = '/var/log/rhsm/rhsmcertd.log'

handler = None
stdout_handler = None

LOG_FORMAT = u'%(asctime)s [%(levelname)s]  @%(filename)s:%(lineno)d - %(message)s'
LOG_LEVEL = logging.DEBUG


def _get_handler():
    # we only need one global handler
    global handler
    if handler is not None:
        return handler

    path = '/var/log/rhsm/rhsm.log'
    try:
        if not os.path.isdir("/var/log/rhsm"):
            os.mkdir("/var/log/rhsm")
    except Exception:
        pass

    # Try to write to /var/log, fallback on console logging:
    try:
        handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5, encoding='utf-8')
    except IOError:
        handler = logging.StreamHandler()
    except Exception:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(LOG_LEVEL)

    return handler


def _get_stdout_handler():
    global stdout_handler
    if stdout_handler is not None:
        return stdout_handler

    handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(logging.DEBUG)

    return handler


def init_logger():
    logging.getLogger().setLevel(LOG_LEVEL)
    logging.getLogger().addHandler(_get_handler())

    # dump logs to stdout, and (re)set log level
    # to DEBUG
    if 'SUBMAN_DEBUG' in os.environ:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(_get_stdout_handler())


def init_logger_for_yum():
    """
    Logging initialization for the yum plugins. we want to grab log output only
    for modules in the python-rhsm package, and subscription manager. let yum
    handle everything else (and don't let yum handle our log output.
    """
    # NOTE: this get's called once by each yum plugin, so
    # return the same global handler in those cases so
    # we don't add two different instances of the handler
    # to the loggers
    log_handler = _get_handler()

    logging.getLogger('rhsm').propagate = False
    logging.getLogger('rhsm').setLevel(logging.DEBUG)
    logging.getLogger('rhsm').addHandler(log_handler)

    logging.getLogger('rhsm-app').propagate = False
    logging.getLogger('rhsm-app').setLevel(logging.DEBUG)
    logging.getLogger('rhsm-app').addHandler(log_handler)
