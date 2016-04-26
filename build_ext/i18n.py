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
import os
import shutil
import subprocess

from distutils import cmd, log
from distutils.command.build_py import build_py as _build_py

from build_ext.utils import Utils


class TransBase(cmd.Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _run(self, cmd):
        rc = subprocess.call(cmd)
        if rc != 0:
            raise RuntimeError("Failed: '%s'" % ' '.join(cmd))


# Courtesy http://wiki.maemo.org/Internationalize_a_Python_application
class BuildTrans(TransBase):
    description = 'Compile .po files into .mo files'
    user_options = _build_py.user_options + [
        ('lint', 'l', 'check po files only'),
    ]

    boolean_options = ['lint']

    def initialize_options(self):
        self.build_base = None
        self.lint = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))

    def compile(self, src, dest):
        log.info("Compiling %s" % src)
        if self.lint:
            dest = '/dev/null'

        cmd = ['msgfmt', '--check', '--statistics', '-o', dest, src]
        self._run(cmd)

    def run(self):
        for po_file in Utils.find_files_of_type('po', '*.po'):
            lang = os.path.basename(po_file)[:-3]
            dest_path = os.path.join(self.build_base, 'locale', lang, 'LC_MESSAGES')
            dest = os.path.join(dest_path, 'rhsm.mo')
            Utils.run_if_new(po_file, dest, self.compile)


class UpdateTrans(TransBase):
    description = 'Update .po files with msgmerge'

    def merge(self, po_file, keys_file):
        log.info("Updating %s" % po_file)
        cmd = ['msgmerge', '-N', '--backup=none', '-U', po_file, keys_file]
        self._run(cmd)

    def run(self):
        keys_file = os.path.join(os.curdir, 'po', 'keys.pot')
        for po_file in Utils.find_files_of_type('po', '*.po'):
            self.merge(po_file, keys_file)


class UniqTrans(TransBase):
    description = 'Unify duplicate translations with msguniq'

    def run(self):
        for po_file in Utils.find_files_of_type('po', '*.po'):
            cmd = ['msguniq', po_file, '-o', po_file]
            self._run(cmd)


class Gettext(TransBase):
    description = 'Extract strings to po files.'
    user_options = _build_py.user_options + [
        ('lint', 'l', 'check po files only'),
    ]

    boolean_options = ['lint']

    def initialize_options(self):
        self.build_base = None
        self.lint = None

    def find_py(self):
        files = []
        files.extend(list(Utils.find_files_of_type('src', '*.py')))
        files.extend(list(Utils.find_files_of_type('bin', '*')))

        # We need to grab some strings out of optparse for translation
        import optparse
        optparse_source = "%s.py" % os.path.splitext(optparse.__file__)[0]
        if not os.path.exists(optparse_source):
            raise RuntimeError("Could not find optparse.py at %s" % optparse_source)
        files.append(optparse_source)

        return files

    def find_c(self):
        files = []
        files.extend(list(Utils.find_files_of_type('src', '*.c')))
        files.extend(list(Utils.find_files_of_type('src', '*.h')))
        files.extend(list(Utils.find_files_of_type('tmp', '*.h')))
        return files

    def find_glade(self):
        files = []
        files.extend(list(Utils.find_files_of_type('src', '*.ui')))
        files.extend(list(Utils.find_files_of_type('src', '*.glade')))
        return files

    def find_desktop(self):
        files = []
        files.extend(list(Utils.find_files_of_type('etc-conf', '*.desktop.in')))
        return files

    def _write_sources(self, manifest_file, find_function):
        with open(manifest_file, 'w') as f:
            f.write('\n'.join(find_function()))
            f.write('\n')

    def run(self):
        manifest_prefix = os.path.join(os.curdir, 'po', 'POTFILES')
        keys_file = os.path.join(os.curdir, 'po', 'keys.pot')
        if self.lint:
            keys_file = '/dev/null'

        # Create xgettext friendly header files from the desktop files.
        # See http://stackoverflow.com/a/23643848/6124862
        cmd = ['intltool-extract', '-l', '--type=gettext/ini']
        for desktop_file in Utils.find_files_of_type('etc-conf', '*.desktop.in'):
            self._run(cmd + [desktop_file])

        cmd = ['xgettext', '--from-code=utf-8', '--sort-by-file', '-o', keys_file]

        # These tuples contain a template for the file name that will contain a list of
        # all source files of a given type to translate, a function that finds all the
        # source files of a given type, the source language to send to xgettext, and a
        # list of any additional arguments.
        trans_types = [
            # The C source files require that we inform xgettext to extract strings from the
            # _() and N_() functions.
            ('%s.c', self.find_c, 'C', ['-k_', '-kN_']),
            ('%s.py', self.find_py, 'Python', []),
            ('%s.glade', self.find_glade, 'Glade', []),
        ]

        for manifest_template, search_func, language, other_options in trans_types:
            manifest = manifest_template % manifest_prefix
            self._write_sources(manifest, search_func)

            specific_opts = ['-f', manifest, '--language', language]
            specific_opts.extend(other_options)
            if os.path.exists(keys_file):
                specific_opts.append('--join-existing')
            log.debug("Running %s" % ' '.join(cmd + specific_opts))
            self._run(cmd + specific_opts)

        # Delete the directory holding the temporary files created by intltool-extract
        shutil.rmtree('tmp')
