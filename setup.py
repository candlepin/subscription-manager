#!/usr/bin/env python
from __future__ import print_function, division, absolute_import

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
import os
import re
import subprocess

from glob import glob
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install as _install


from distutils import log
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build
from distutils.command.clean import clean as _clean
from distutils.command.build_py import build_py as _build_py
from distutils.dir_util import remove_tree

from build_ext import i18n, lint, template
from build_ext.utils import Utils


# subclass build_py so we can generate
# version.py based on either args passed
# in (--rpm-version, --gtk-version) or
# from a guess generated from 'git describe'
class rpm_version_release_build_py(_build_py):
    user_options = _build_py.user_options + [
        ('gtk-version=', None, 'GTK version this is built for'),
        ('rpm-version=', None, 'version and release of the RPM this is built for')]

    def initialize_options(self):
        _build_py.initialize_options(self)
        self.rpm_version = None
        self.gtk_version = None
        self.versioned_packages = []

    def finalize_options(self):
        _build_py.finalize_options(self)
        self.set_undefined_options('build', ('rpm_version', 'rpm_version'), ('gtk_version', 'gtk_version'))

    def run(self):
        log.info("Building with GTK_VERSION=%s and RPM_VERSION=%s" % (self.gtk_version, self.rpm_version))
        _build_py.run(self)
        # create a "version.py" that includes the rpm version
        # info passed to our new build_py args
        if not self.dry_run:
            for package in self.versioned_packages:
                version_dir = os.path.join(self.build_lib, package)
                version_file = os.path.join(version_dir, 'version.py')
                try:
                    lines = []
                    with open(version_file, 'r') as f:
                        for l in f.readlines():
                            l = l.replace("RPM_VERSION", str(self.rpm_version))
                            l = l.replace("GTK_VERSION", str(self.gtk_version))
                            lines.append(l)

                    with open(version_file, 'w') as f:
                        for l in lines:
                            f.write(l)
                except EnvironmentError:
                    raise


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


class install(_install):
    user_options = _install.user_options + [
        ('gtk-version=', None, 'GTK version this is built for'),
        ('rpm-version=', None, 'version and release of the RPM this is built for'),
        ('with-systemd=', None, 'whether to install w/ systemd support or not')]

    def initialize_options(self):
        _install.initialize_options(self)
        self.rpm_version = None
        self.gtk_version = None
        self.with_systemd = None

    def finalize_options(self):
        _install.finalize_options(self)
        self.set_undefined_options('build', ('rpm_version', 'rpm_version'), ('gtk_version', 'gtk_version'))


class build(_build):
    user_options = _build.user_options + [
        ('gtk-version=', None, 'GTK version this is built for'),
        ('rpm-version=', None, 'version and release of the RPM this is built for')]

    def initialize_options(self):
        _build.initialize_options(self)
        self.rpm_version = None
        self.gtk_version = None
        self.git_tag_prefix = "subscription-manager-"

    def finalize_options(self):
        _build.finalize_options(self)
        if not self.rpm_version:
            self.rpm_version = self.get_git_describe()

        if not self.gtk_version:
            self.gtk_version = self.get_gtk_version()

    def get_git_describe(self):
        try:
            cmd = ["git", "describe"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            output = process.communicate()[0].decode('utf-8').strip()
            if output.startswith(self.git_tag_prefix):
                return output[len(self.git_tag_prefix):]
        except OSError:
            # When building the RPM there won't be a git repo to introspect so
            # builders *must* specify the version via the --rpm-version option
            return "unknown"

    def get_gtk_version(self):
        cmd = ['rpm', '--eval=%dist']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output = process.communicate()[0].decode('utf-8').strip()
        if re.search('el6', output):
            return "2"
        return "3"

    def has_po_files(self):
        try:
            next(Utils.find_files_of_type('po', '*.po'))
            return True
        except StopIteration:
            return False

    sub_commands = _build.sub_commands + [('build_trans', has_po_files), ('build_template', lambda arg: True)]


class install_data(_install_data):
    """Used to intelligently install data files.  For example, files that must be generated (such as .mo files
    or desktop files with merged translations) or an entire tree of data files.
    """
    user_options = _install_data.user_options + [
        ('with-systemd=', None, 'whether to install w/ systemd support or not')]

    def initialize_options(self):
        _install_data.initialize_options(self)
        self.with_systemd = None
        # Can't use super() because Command isn't a new-style class.

    def finalize_options(self):
        _install_data.finalize_options(self)
        self.set_undefined_options('install', ('with_systemd', 'with_systemd'))
        if self.with_systemd is None:
            self.with_systemd = True  # default to True
        else:
            self.with_systemd = self.with_systemd == 'true'

    def run(self):
        self.add_messages()
        self.add_desktop_files()
        self.add_icons()
        self.add_dbus_service_files()
        self.add_systemd_services()
        _install_data.run(self)

    def join(self, *args):
        return os.path.normpath(os.path.join(*args))

    def add_messages(self):
        for lang in os.listdir(self.join('build', 'locale')):
            lang_dir = self.join('share', 'locale', lang, 'LC_MESSAGES')
            lang_file = self.join('build', 'locale', lang, 'LC_MESSAGES', 'rhsm.mo')
            self.data_files.append((lang_dir, [lang_file]))

    def add_desktop_files(self):
        desktop_dir = self.join('share', 'applications')
        desktop_file = self.join('build', 'applications', 'subscription-manager-gui.desktop')
        self.data_files.append((desktop_dir, [desktop_file]))

        # Installing files outside of the "prefix" with setuptools looks to be flakey:
        # See https://github.com/pypa/setuptools/issues/460.  However, this seems to work
        # so I'm making an exception to the "everything outside the prefix should be handled
        # by make" policy.
        autostart_dir = self.join('/etc', 'xdg', 'autostart')
        autostart_file = self.join('build', 'autostart', 'rhsm-icon.desktop')
        self.data_files.append((autostart_dir, [autostart_file]))

    def add_dbus_service_files(self):
        dbus_service_directory = self.join('share', 'dbus-1', 'system-services')
        if self.with_systemd:
            source_dir = self.join('build', 'dbus', 'system-services-systemd')
        else:
            source_dir = self.join('build', 'dbus', 'system-services')
        for file in os.listdir(source_dir):
            self.data_files.append((dbus_service_directory, [self.join(source_dir, file)]))

    def add_systemd_services(self):
        if not self.with_systemd:
            return  # if we're not installing for systemd, stop!
        systemd_install_directory = self.join('lib', 'systemd', 'system')
        source_dir = self.join('build', 'dbus', 'systemd')
        for file in os.listdir(self.join('build', 'dbus', 'systemd')):
            self.data_files.append((systemd_install_directory, [self.join(source_dir, file)]))

    def add_icons(self):
        icon_source_root = self.join('src', 'subscription_manager', 'gui', 'data', 'icons', 'hicolor')
        for d in os.listdir(icon_source_root):
            icon_dir = self.join('share', 'icons', 'hicolor', d, 'apps')
            icon_source_files = glob(self.join(icon_source_root, d, 'apps', 'subscription-manager.*'))

            self.data_files.append((icon_dir, icon_source_files))


setup_requires = []

install_requires = [
        'six',
        'kitchen',
    ]

test_require = [
      'mock',
      'nose',
      'nose-capturestderr',
      'nose-randomly',
      'coverage',
      'polib',
      'freezegun',
      'flake8',
      'lxml',
    ] + install_requires + setup_requires

cmdclass = {
    'clean': clean,
    'install': install,
    'install_data': install_data,
    'build': build,
    'build_py': rpm_version_release_build_py,
    'build_trans': i18n.BuildTrans,
    'build_template': template.BuildTemplate,
    'update_trans': i18n.UpdateTrans,
    'uniq_trans': i18n.UniqTrans,
    'gettext': i18n.Gettext,
    'lint': lint.Lint,
    'lint_glade': lint.GladeLint,
    'lint_rpm': lint.RpmLint,
    'flake8': lint.PluginLoadingFlake8
}

setup(
    name="subscription-manager",
    version='1.21.2',
    url="http://www.candlepinproject.org",
    description="Manage subscriptions for Red Hat products.",
    license="GPLv2",
    author="Adrian Likins",
    author_email="alikins@redhat.com",
    cmdclass=cmdclass,
    packages=find_packages('src', exclude=['subscription_manager.gui.firstboot.*', '*.ga_impls', '*.ga_impls.*', '*.plugin.ostree', '*.services.examples']),
    package_dir={'': 'src'},
    package_data={
        'subscription_manager.gui': ['data/glade/*.glade', 'data/ui/*.ui', 'data/icons/*.svg'],
    },
    entry_points={
        'console_scripts': [
            'subscription-manager = subscription_manager.scripts.subscription_manager:main',
            'rhn-migrate-classic-to-rhsm = subscription_manager.scripts.rhn_migrate_classic_to_rhsm:main',
            'rct = subscription_manager.scripts.rct:main',
            'rhsm-debug = subscription_manager.scripts.rhsm_debug:main',
            'rhsm-facts-service = subscription_manager.scripts.rhsm_facts_service:main',
            'rhsm-service = subscription_manager.scripts.rhsm_service:main',
            'rhsmcertd-worker = subscription_manager.scripts.rhsmcertd_worker:main',
            'rhsmd = subscription_manager.scripts.rhsm_d:main',
        ],
        'gui_scripts': [
            'subscription-manager-gui = subscription_manager.scripts.subscription_manager_gui:main',
        ],
    },
    data_files=[
        # sat5to6 is packaged separately
        ('share/man/man8', set(glob('man/*.8')) - set(['man/sat5to6.8'])),
        ('share/man/man5', glob('man/*.5')),
        ('share/gnome/help/subscription-manager/C', glob('docs/*.xml')),
        ('share/gnome/help/subscription-manager/C/figures', glob('docs/figures/*.png')),
        ('share/omf/subscription-manager', glob('docs/*.omf')),
    ],
    command_options={
        'egg_info': {
            'egg_base': ('setup.py', os.curdir),
        },
        'build_py': {
            'versioned_packages': ('setup.py', ['subscription_manager', 'rct']),
        },
    },
    include_package_data=True,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=test_require,
    ext_modules=[Extension('rhsm._certificate', ['src/certificate.c'],
                           libraries=['ssl', 'crypto'])],
    test_suite='nose.collector',
)
