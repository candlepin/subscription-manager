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

cmdclass = {
    'build_trans': i18n.BuildTrans,
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
    version="1.22.1",
    url="http://www.candlepinproject.org",
    description="Manage Red Hat System Purpose",
    license="GPLv2",
    author="Chris Snyder",
    author_email="chainsaw@redhat.com",
    cmdclass=cmdclass,
    packages=find_packages('src', include=["syspurpose"]),
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
