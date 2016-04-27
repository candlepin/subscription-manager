# Copyright (c) 2016 Red Hat, Inc.
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
import re

from distutils.text_file import TextFile

from build_ext.utils import Utils, BaseCommand


class Lint(BaseCommand):
    description = "examine code for errors"

    def has_pure_modules(self):
        return self.distribution.has_pure_modules()

    def has_glade_files(self):
        try:
            next(Utils.find_files_of_type('src', '*.glade'))
            return True
        except StopIteration:
            return False

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

    # Defined at the end since it references unbound methods
    sub_commands = [
        ('lint_glade', has_glade_files),
        ('flake8', has_pure_modules),
    ]


class GladeLint(BaseCommand):
    """See BZ #826874.  Certain attributes cause issues on older libglade."""
    description = "check Glade files for common errors"

    def scan_file(self, f):
        text_file = TextFile(f)
        for line in iter(text_file.readline, None):
            if re.search('swapped="no"', line):
                text_file.warn("Found 'swapped=\"no\": %s" % line)
            if re.search('property name="orientation"', line):
                text_file.warn("Found 'property name=\"orientation\": %s" % line)

    def run(self):
        for f in Utils.find_files_of_type('src', '*.glade'):
            self.scan_file(f)
