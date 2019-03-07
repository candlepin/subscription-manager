from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

import os
import string
import subprocess

from distutils import log

from build_ext.utils import Utils, BaseCommand


class BuildTemplate(BaseCommand):
    description = 'Template files. Variables used from build_ext/template.py'

    def initialize_options(self):
        self.build_base = None
        self.vars = {}
        self.vars['libexecdir'] = self.get_libexecdir()

    def get_libexecdir(self):
        try:
            cmd = ['rpm', '--eval=%_libexecdir']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            return process.communicate()[0].strip().decode('UTF-8', 'strict')
        except OSError:
            return 'libexec'

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))

    def template(self, src, dest):
        log.debug("Templating file %s" % dest)

        with open(src, 'r') as template_file:
            template_text = template_file.read()
        template = string.Template(template_text)

        base_directory = os.path.dirname(dest)
        if not os.path.exists(base_directory):
            os.makedirs(base_directory)

        with open(dest, 'w') as output:
            output_text = template.substitute(self.vars)
            output.write(output_text)

    def run(self):
        for template in Utils.find_files_of_type('etc-conf', '*.template'):
            dest_rel_path = os.path.relpath("%s" % os.path.splitext(template)[0], 'etc-conf')
            dest = os.path.join(self.build_base, dest_rel_path)
            Utils.run_if_new(template, dest, self.template)
