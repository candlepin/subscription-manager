from __future__ import print_function, division, absolute_import

#
# Make optparse friendlier to i18n/l10n
#
# Copyright (c) 2010 Red Hat, Inc.
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

"""
Make optparse friendlier to i18n/l10n

Just use this instead of optparse, the interface should be the same.

For some backgorund, see:
http://bugs.python.org/issue4319
"""
import optparse
from optparse import IndentedHelpFormatter as _IndentedHelpFormatter
from optparse import OptionParser as _OptionParser
import sys
import textwrap

from subscription_manager.i18n import ugettext as _


optparse._ = _

# note default is lower caps
USAGE = _("%prog [OPTIONS]")


#
# This is pulled from the python dist, in optparse.py
#
#Copyright (c) 2001-2006 Gregory P. Ward.  All rights reserved.
#Copyright (c) 2002-2006 Python Software Foundation.  All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are
#met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
#  * Neither the name of the author nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
#TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
class WrappedIndentedHelpFormatter(_IndentedHelpFormatter):
    def __init__(self, indent_increment=2,
                 max_help_position=24, width=None,
                 short_first=1):

        _IndentedHelpFormatter.__init__(
            self, indent_increment, max_help_position, width, short_first)

    # FIXME: This is a hack, since optparse doesn't let us change textwrap
    #        params directly, and textwrap is kind of broken trying to
    #        break words with multibyte chars.
    #        See bz #752316, #771751
    #
    # So we add our own HelpFormatter subclass, and since we can't really
    # change how it calls textwrap, duplicate it here, and change the
    # textwrap.wrap call to include the break_long_words=False
    def format_option(self, option):
        # The help for each option consists of two parts:
        #   * the opt strings and metavars
        #     eg. ("-x", or "-fFILENAME, --file=FILENAME")
        #   * the user-supplied help string
        #     eg. ("turn on expert mode", "read data from FILENAME")
        #
        # If possible, we write both of these on the same line:
        #   -x      turn on expert mode
        #
        # But if the opt string list is too long, we put the help
        # string on a second line, indented to the same column it would
        # start in if it fit on the first line.
        #   -fFILENAME, --file=FILENAME
        #           read data from FILENAME
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = textwrap.wrap(help_text, self.help_width,
                                       break_long_words=False)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(["%*s%s\n" % (self.help_position, "", line)
                           for line in help_lines[1:]])
        elif opts[-1] != "\n":
            result.append("\n")
        return "".join(result)

    # 2.4 uses lower case "usage", 2.6 uses "Usage"
    # This was making QE jittery, always use upper
    def format_usage(self, usage):
        return _("Usage: %s\n") % usage


class OptionParser(_OptionParser):

    def print_help(self):
        sys.stdout.write(self.format_help())

    def error(self, msg):
        """
        Override default error handler to localize

        prints command usage, then the error string, and exits.
        """
        self.print_usage(sys.stderr)
        #translators: arg 1 is the program name, arg 2 is the error message
        print(_("%s: error: %s") % (self.get_prog_name(), msg))
        self.exit(2)
