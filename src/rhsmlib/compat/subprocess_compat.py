from __future__ import print_function, division, absolute_import

# Copyright (c) 2010-2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
#
# Compat module that implements a subprocess.check_output work-a-like for
# python 2.6.

import logging
import subprocess
import six

log = logging.getLogger(__name__)


def check_output_2_6(*args, **kwargs):
    cmd_args = kwargs.get('args', None) or args[0]

    log.debug("Running '%s'" % cmd_args)

    process = subprocess.Popen(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    (std_output, std_error) = process.communicate()

    output = std_output.strip()

    returncode = process.poll()
    if returncode:
        raise subprocess.CalledProcessError(returncode, cmd_args)

    return output


def check_output_six(*args, **kwargs):
    output = subprocess.check_output(*args, **kwargs)
    if six.PY3 and isinstance(output, bytes):
        output = output.decode('utf-8')
    return output


check_output = check_output_2_6

if hasattr(subprocess, 'check_output'):
    check_output = check_output_six
