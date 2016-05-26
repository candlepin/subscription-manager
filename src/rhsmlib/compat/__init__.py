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

log = logging.getLogger(__name__)


def check_output_2_6(*args, **kwargs):
    cmd_args = kwargs.get('args', None) or args[0]

    log.debug("Running '%s'" % cmd_args)

    process = subprocess.Popen(*args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               **kwargs)
    (std_output, std_error) = process.communicate()

    log.debug("%s stdout: %s" % (cmd_args, std_output))
    log.debug("%s stderr: %s" % (cmd_args, std_error))

    output = std_output.strip()

    returncode = process.poll()
    if returncode:
        raise CalledProcessError(returncode, cmd_args,
                                 output=output)

    return output


# FIXME: ditto, move or remove
# Exception classes used by this module.
# from later versions of subprocess, but not there on 2.4, so include our version
class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)

check_output = check_output_2_6

if hasattr(subprocess, 'check_output'):
    check_output = subprocess.check_output
