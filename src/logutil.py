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
from logging import Formatter
from logging.handlers import RotatingFileHandler


def getLogger(name):
    path = '/var/log/rhsm/rhsm.log'
    fmt = '%(asctime)s [%(levelname)s] %(funcName)s() @%(filename)s:%(lineno)d - %(message)s'
    handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5)
    handler.setFormatter(Formatter(fmt))
    log = logging.getLogger(name)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log