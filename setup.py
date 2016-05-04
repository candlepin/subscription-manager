#!/usr/bin/env python

#
# Copyright (c) 2014 Red Hat, Inc.
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
import fnmatch
import os
import subprocess

from glob import glob
from setuptools import setup, find_packages

from distutils import log
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build
from distutils.command.clean import clean as _clean
from distutils.command.build_py import build_py as _build_py
from distutils.dir_util import remove_tree

from build_ext import i18n, lint


# subclass build_py so we can generate
# version.py based on either args passed
# in (--rpm-version, --rpm-release) or
# from a guess generated from 'git describe'
class rpm_version_release_build_py(_build_py):
    user_options = _build_py.user_options + [
        ('rpm-version=', None, 'version of the rpm this is built for'),
        ('rpm-release=', None, 'release of the rpm this is built for')]

    def initialize_options(self):
        _build_py.initialize_options(self)
        self.rpm_version = os.getenv('PYTHON_SUBMAN_VERSION')
        self.rpm_release = os.getenv('PYTHON_SUBMAN_RELEASE')
        self.git_tag_prefix = "subscription-manager"
        self.version_module_sub_dir = ""

    def get_git_describe(self):
        cmd = ["git", "describe"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output = process.communicate()[0].strip()
        if output.startswith(self.git_tag_prefix):
            return output[len(self.git_tag_prefix):]
        return 'unknown'

    def run(self):
        # create a "version.py" that includes the rpm version
        # info passed to our new build_py args
        if not self.dry_run:
            version_dir = os.path.join(self.build_lib, self.version_module_sub_dir)
            version_file = os.path.join(version_dir, 'version.py')
            version_release = "unknown"
            if self.rpm_version and self.rpm_release:
                version_release = "%s-%s" % (self.rpm_version,
                                               self.rpm_release)
            else:
                version_release = self.get_git_describe()
            try:
                self.mkpath(version_dir)
                f = open(version_file, 'w')
                f.write("rpm_version = '%s'\n" % version_release)
                f.close()
            except EnvironmentError:
                raise
        _build_py.run(self)


class clean(_clean):
    def initialize_options(self):
        self.egg_base = None
        _clean.initialize_options(self)

    def finalize_options(self):
        self.set_undefined_options('egg_info', ('egg_base', 'egg_base'))
        _clean.finalize_options(self)

    def run(self):
        if self.all:
            for f in glob(os.path.join(self.egg_base, '*.egg-info')):
                log.info("removing %s" % f)
                remove_tree(f, dry_run=self.dry_run)
        _clean.run(self)


class build(_build):
    sub_commands = _build.sub_commands + [('build_trans', None)]

    def run(self):
        _build.run(self)


class install_data(_install_data):
    """Used to install data files that must be generated such as .mo files or desktop files
    with merged translations.
    """

    def initialize_options(self):
        self.transforms = None
        # Can't use super() because Command isn't a new-style class.
        _install_data.initialize_options(self)

    def finalize_options(self):
        if self.transforms is None:
            self.transforms = []
        _install_data.finalize_options(self)

    def run(self):
        self.add_messages()
        self.add_desktop_files()
        _install_data.run(self)
        self.transform_files()

    def transform_files(self):
        for file_glob, new_extension in self.transforms:
            matches = fnmatch.filter(self.outfiles, file_glob)
            for f in matches:
                out_dir = os.path.dirname(f)
                out_name = os.path.basename(f).split('.')[0] + new_extension
                self.move_file(f, os.path.join(out_dir, out_name))

    def add_messages(self):
        for lang in os.listdir('build/locale/'):
            lang_dir = os.path.join('share', 'locale', lang, 'LC_MESSAGES')
            lang_file = os.path.join('build', 'locale', lang, 'LC_MESSAGES', 'rhsm.mo')
            self.data_files.append((lang_dir, [lang_file]))

    def add_desktop_files(self):
        desktop_dir = os.path.join('share', 'applications')
        desktop_file = os.path.join('build', 'applications', 'subscription-manager-gui.desktop')
        self.data_files.append((desktop_dir, [desktop_file]))

        autostart_dir = os.path.join('/etc', 'xdg', 'autostart')
        autostart_file = os.path.join('build', 'autostart', 'rhsm-icon.desktop')
        self.data_files.append((autostart_dir, [autostart_file]))

setup_requires = ['flake8']

install_requires = []

test_require = [
      'mock',
      'nose',
      'coverage',
      'polib',
      'freezegun',
    ] + install_requires + setup_requires

cmdclass = {
    'clean': clean,
    'install_data': install_data,
    'build': build,
    'build_py': rpm_version_release_build_py,
    'build_trans': i18n.BuildTrans,
    'update_trans': i18n.UpdateTrans,
    'uniq_trans': i18n.UniqTrans,
    'gettext': i18n.Gettext,
    'lint': lint.Lint,
    'lint_glade': lint.GladeLint,
    'lint_rpm': lint.RpmLint,
    'flake8': lint.PluginLoadingFlake8Command
}

transforms = [
    ('*.completion.sh', '.sh'),
    ('*.pam', ''),
    ('*.console', ''),
]

setup(
    name="subscription-manager",
    version='1.17.6',
    url="http://candlepinproject.org",
    description="Manage subscriptions for Red Hat products.",
    license="GPLv2",
    author="Adrian Likins",
    author_email="alikins@redhat.com",
    cmdclass=cmdclass,
    packages=find_packages('src', exclude=['subscription_manager.gui.firstboot']),
    package_dir={'': 'src'},
    data_files=[
        ('sbin', ['bin/subscription-manager', 'bin/subscription-manager-gui', 'bin/rhn-migrate-classic-to-rhsm']),
        ('bin', ['bin/rct', 'bin/rhsm-debug']),
        ('share/man/man8', glob('man/*.8')),
        ('share/gnome/help/subscription-manager/C', glob('docs/*.xml')),
        ('share/gnome/help/subscription-manager/C/figures', glob('docs/figures/*.png')),
        ('share/omf/subscription-manager', glob('docs/*.omf')),
        ('/etc/rhsm', ['etc-conf/rhsm.conf']),
        ('/etc/pam.d', glob('etc-conf/*.pam')),
        ('/etc/logrotate.d/subscription-manager', ['etc-conf/logrotate.conf']),
        ('/etc/yum/pluginconf.d', glob('etc-conf/plugin/*.conf')),
        ('/etc/bash_completion.d', glob('etc-conf/*.completion.sh')),
        ('/etc/security/console.apps', glob('etc-conf/*.console')),
    ],
    command_options={
        'install_data': {
            'transforms': ('setup.py', transforms),
        },
        'egg_info': {
            'egg_base': ('setup.py', os.curdir),
        },
    },
    include_package_data=True,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=test_require,
    test_suite='nose.collector',
)
