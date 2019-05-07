#! /usr/bin/env python3
#
# Copyright (c) 2018 Red Hat, Inc.
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
from setuptools import setup, find_packages

import sys
import os
from glob import glob

# Note that importing build_ext alone won't be enough to make certain tasks (like lint) work
# those tasks require that some dependencies (e.g. lxml) be installed.  Munging the syspath
# here is just so that setup.py will be able to load and run in Jenkins jobs and RPM builds
# that don't do pip install -r test-requirements.txt
build_ext_home = os.path.abspath(os.path.join(os.path.dirname(__file__), "../build_ext"))
sys.path.append(build_ext_home)
from build_ext import i18n, utils

from distutils.command.build import build as _build
from distutils.command.install_data import install_data as _install_data


class install_data(_install_data):
    def join(self, *args):
        return os.path.normpath(os.path.join(*args))

    def add_messages(self):
        for lang in os.listdir(self.join('build', 'locale')):
            lang_dir = self.join('share', 'locale', lang, 'LC_MESSAGES')
            lang_file = self.join('build', 'locale', lang, 'LC_MESSAGES', 'syspurpose.mo')
            self.data_files.append((lang_dir, [lang_file]))

    def run(self):
        self.add_messages()
        _install_data.run(self)


class build(_build):

    def has_po_files(self):
        try:
            next(utils.Utils.find_files_of_type('po', '*.po'))
            return True
        except StopIteration:
            return False
    # Based on the po extensions for subscription-manager
    # adding items to this class attribute allow these commands to be run along with this command
    sub_commands = _build.sub_commands + [('build_trans', has_po_files)]


class BuildTrans(i18n.BuildTrans):
    app_name = "syspurpose"


cmdclass = {
    'build_trans': BuildTrans,
    'build': build,
    'install_data': install_data,
    'update_trans': i18n.UpdateTrans,
    'uniq_trans': i18n.UniqTrans,
    'gettext': i18n.Gettext,
    'clean': utils.clean,
}
setup_requires = []

test_require = [
    'mock',
    'nose',
    'nose-randomly',
    'nose-capturestderr'
]

setup(
    name="syspurpose",
    version="1.25.5",
    url="http://www.candlepinproject.org",
    description="Manage Red Hat System Purpose",
    license="GPLv2",
    author="Chris Snyder",
    author_email="chainsaw@redhat.com",
    cmdclass=cmdclass,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    tests_require=test_require,
    setup_requires=setup_requires,
    test_suite='nose.collector',
    data_files=[
        ('share/man/man8', glob('man/*.8'))
    ],
    entry_points={
        "console_scripts": [
            "syspurpose = syspurpose.main:main"
        ]
    }
)
