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

import os
import logging

from logging import Formatter
from logging.handlers import RotatingFileHandler

CERT_LOG = '/var/log/rhsm/rhsmcertd.log'


def _get_handler():
    path = '/var/log/rhsm/rhsm.log'
    try:
        if not os.path.isdir("/var/log/rhsm"):
            os.mkdir("/var/log/rhsm")
    except:
        pass
    fmt = u'%(asctime)s [%(levelname)s]  @%(filename)s:%(lineno)d - %(message)s'

    # Try to write to /var/log, fallback on console logging:
    try:
        handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5, encoding='utf-8')
    except IOError:
        handler = logging.StreamHandler()
    except:
        handler = logging.StreamHandler()

    handler.setFormatter(Formatter(fmt))
    handler.setLevel(logging.DEBUG)

    return handler


def init_logger():
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(_get_handler())


def init_logger_for_yum():
    """
    Logging initialization for the yum plugins. we want to grab log output only
    for modules in the python-rhsm package, and subscription manager. let yum
    handle everything else (and don't let yum handle our log output.
    """
    handler = _get_handler()

    logging.getLogger('rhsm').propagate = False
    logging.getLogger('rhsm').setLevel(logging.DEBUG)
    logging.getLogger('rhsm').addHandler(handler)

    logging.getLogger('rhsm-app').propagate = False
    logging.getLogger('rhsm-app').setLevel(logging.DEBUG)
    logging.getLogger('rhsm-app').addHandler(handler)
