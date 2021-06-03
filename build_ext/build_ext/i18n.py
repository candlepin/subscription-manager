from __future__ import print_function, division, absolute_import

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

from distutils import log, dir_util
from distutils.command.build_py import build_py as _build_py
from distutils.spawn import spawn

from build_ext.utils import Utils, BaseCommand


# Courtesy http://wiki.maemo.org/Internationalize_a_Python_application
class BuildTrans(BaseCommand):
    description = 'Compile .po files into .mo files'
    user_options = _build_py.user_options + [
        ('lint', 'l', 'check po files only'),
    ]

    boolean_options = ['lint']
    app_name = "rhsm"

    def initialize_options(self):
        self.build_base = None
        self.lint = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))

    def compile(self, src, dest):
        log.debug("Compiling %s" % src)
        if self.lint:
            dest = '/dev/null'

        cmd = ['msgfmt', '--check', '--statistics', '-o', dest, src]
        spawn(cmd)

    def merge_desktop(self, src, dest):
        log.debug("Merging desktop file %s" % src)
        if self.lint:
            dest = '/dev/null'

        cmd = ['intltool-merge', '-d', 'po', src, dest]
        spawn(cmd)

    def run(self):
        for po_file in Utils.find_files_of_type('po', '*.po'):
            lang = os.path.basename(po_file)[:-3]
            dest_path = os.path.join(self.build_base, 'locale', lang, 'LC_MESSAGES')
            dest = os.path.join(dest_path, self.app_name + '.mo')
            Utils.run_if_new(po_file, dest, self.compile)

        for desktop_file in Utils.find_files_of_type('etc-conf', '*.desktop.in'):
            output_file = os.path.basename("%s" % os.path.splitext(desktop_file)[0])

            dest_path = os.path.join(self.build_base, 'applications')
            if output_file == 'rhsm-icon.desktop':
                dest_path = os.path.join(self.build_base, 'autostart')
            dest = os.path.join(dest_path, output_file)
            Utils.run_if_new(desktop_file, dest, self.merge_desktop)


class UpdateTrans(BaseCommand):
    description = 'Update .po files with msgmerge'
    user_options = _build_py.user_options + [
        ('key-file=', 'k', 'file to update'),
    ]

    def initialize_options(self):
        self.key_file = os.path.join(os.curdir, 'po', 'keys.pot')

    def merge(self, po_file, key_file):
        log.debug("Updating %s" % po_file)
        cmd = ['msgmerge', '-N', '--backup=none', '-U', po_file, self.key_file]
        spawn(cmd)

    def run(self):
        for po_file in Utils.find_files_of_type('po', '*.po'):
            self.merge(po_file, self.key_file)


class UniqTrans(BaseCommand):
    description = 'Unify duplicate translations with msguniq'

    def run(self):
        for po_file in Utils.find_files_of_type('po', '*.po'):
            cmd = ['msguniq', po_file, '-o', po_file]
            spawn(cmd)


class Gettext(BaseCommand):
    description = 'Extract strings to po files.'
    user_options = _build_py.user_options + [
        ('lint', 'l', 'check po files only'),
        ('key-file=', 'k', 'file to write to'),
    ]

    boolean_options = ['lint']

    def initialize_options(self):
        self.build_base = None
        self.lint = None
        self.key_file = os.path.join(os.curdir, 'po', 'keys.pot')

    def finalize_options(self):
        self.src_dirs = self.distribution.package_dir
        print()
        if self.lint:
            self.key_file = '/dev/null'

    def find_py(self):
        files = []

        for src in self.src_dirs.values():
            print(src)
            files.extend(list(Utils.find_files_of_type(src, '*.py')))

        files.extend(list(Utils.find_files_of_type('bin', '*')))
        return files

    def find_c(self):
        files = []

        for src in self.src_dirs.values():
            files.extend(list(Utils.find_files_of_type(src, '*.c', '*.h')))

        files.extend(list(Utils.find_files_of_type('tmp', '*.h')))
        return files

    def find_glade(self):
        files = []
        for src in self.src_dirs.values():
            files.extend(list(Utils.find_files_of_type(src, '*.ui', '*.glade')))
        return files

    def find_js(self):
        files = []
        files.extend(list(Utils.find_files_of_type('cockpit/src', '*.js', '*.jsx')))
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

        # Begin with a fresh key file
        dir_util.mkpath('tmp')
        if self.lint:
            tmp_key_file = self.key_file
        else:
            tmp_key_file = os.path.join('tmp', os.path.basename(self.key_file))

        # Create xgettext friendly header files from the desktop files.
        # See http://stackoverflow.com/a/23643848/6124862
        cmd = ['intltool-extract', '-l', '--type=gettext/ini']
        for desktop_file in Utils.find_files_of_type('etc-conf', '*.desktop.in'):
            spawn(cmd + [desktop_file])

        cmd = ['xgettext', '--from-code=utf-8', '--add-comments=TRANSLATORS:', '--sort-by-file',
               '-o', tmp_key_file, '--package-name=rhsm']

        # These tuples contain a template for the file name that will contain a list of
        # all source files of a given type to translate, a function that finds all the
        # source files of a given type, the source language to send to xgettext, and a
        # list of any additional arguments.
        #
        # ProTip: Use extensions that won't be confused with source files.
        trans_types = [
            # The C source files require that we inform xgettext to extract strings from the
            # _() and N_() functions.
            ('%s.c_files', self.find_c, 'C', ['-k_', '-kN_']),
            ('%s.py_files', self.find_py, 'Python', []),
            ('%s.glade_files', self.find_glade, 'Glade', []),
            ('%s.js_files', self.find_js, 'JavaScript', []),
        ]

        for manifest_template, search_func, language, other_options in trans_types:
            manifest = manifest_template % manifest_prefix
            self._write_sources(manifest, search_func)

            specific_opts = ['-f', manifest, '--language', language]
            specific_opts.extend(other_options)
            if os.path.exists(tmp_key_file):
                specific_opts.append('--join-existing')
            log.debug("Running %s" % ' '.join(cmd + specific_opts))
            spawn(cmd + specific_opts)

        if not self.lint:
            shutil.copy2(tmp_key_file, self.key_file)

        # Delete the directory holding the temporary files created by intltool-extract
        # and the temporary keys.pot
        shutil.rmtree('tmp')


class GettextWithArgparse(Gettext):
    def find_py(self):
        # Can't use super since we're descended from a old-style class
        files = Gettext.find_py(self)

        # We need to grab some strings out of argparse for translation
        import argparse
        argparse_source = "%s.py" % os.path.splitext(argparse.__file__)[0]
        if not os.path.exists(argparse_source):
            raise RuntimeError("Could not find argparse.py at %s" % argparse_source)
        files.append(argparse_source)
        return files
