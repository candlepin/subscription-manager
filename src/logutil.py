#
# Copyright (C) 2005-2008 Red Hat, Inc.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# Jeff Ortel (jortel@redhat.com)
#

import os
import logging
import string
import traceback

from logging import Formatter
from logging.handlers import RotatingFileHandler

CERT_LOG = '/var/log/rhsm/rhsmcertd.log'

def trace_me():
    x = traceback.extract_stack()
    bar = string.join(traceback.format_list(x))
    return bar
    

def trace_me_more():
    frames = traceback.extract_stack()
    stack = "\n"
    for frame in frames:
        stack = stack + "%s:%s\n" % (os.path.basename(frame[0]), frame[2])
    stack = stack + "\n"
    return stack


def _get_handler():
    path = '/var/log/rhsm/rhsm.log'
    if not os.path.isdir("/var/log/rhsm"):
        os.mkdir("/var/log/rhsm")
    fmt = '%(asctime)s [%(levelname)s]  @%(filename)s:%(lineno)d - %(message)s'

    # Try to write to /var/log, fallback on console logging:
    try:
        handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5)
    except IOError, e:
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
